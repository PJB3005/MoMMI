import asyncio
import asyncio.streams
import hmac
import json
import logging
import struct
from hashlib import sha512
from typing import Dict, Tuple, Any, TYPE_CHECKING, Callable, Awaitable
from .handler import MHandler
from .server import MChannel


DIGEST_SIZE = sha512().digest_size

ERROR_OK = struct.pack("!B", 0)
ERROR_ID = struct.pack("!B", 1)
ERROR_PACK = struct.pack("!B", 2)
ERROR_HMAC = struct.pack("!B", 3)
ERROR_UNKNOWN = struct.pack("!B", 4)

logger = logging.getLogger(__name__)


class commloop(object):
    if TYPE_CHECKING:
        from .master import MoMMI

    def __init__(self, master: "MoMMI"):
        self.server = None  # type: asyncio.Server
        self.clients = {}  # type:  Dict[asyncio.Task, Tuple[asyncio.StreamReader, asyncio.StreamWriter]]

        self.master = master  # type: MoMMI

        self.routing = master.config.get_main("commloop.route", {})  # type: Dict[str, Any]
        self.address = master.config.get_main("commloop.address", "localhost")  # type: str
        self.port = master.config.get_main("commloop.port", "localhost")  # type: int
        self.authkey = master.config.get_main("commloop.password", "localhost")  # type: str

    async def start(self, loop: asyncio.AbstractEventLoop):
        self.server = await asyncio.start_server(
            self.accept_client,
            self.address,
            self.port,
            loop=loop
        )
        logger.debug("Started the commloop server.")

    async def stop(self):
        await self.server.wait_closed()

    def accept_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        logger.debug("Accepting new client!")
        task: asyncio.Task = asyncio.Task(self.handle_client(client_reader, client_writer))
        self.clients[task] = (client_reader, client_writer)

        def client_done(task):
            logger.debug("Dropping client connection.")
            del self.clients[task]

        task.add_done_callback(client_done)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            data = await reader.read(2)  # Read ID.
            if data != b"\x30\x05":
                writer.write(ERROR_ID)
                return

            logger.debug(f"Got ID packets: {data}.")

            auth = await reader.read(DIGEST_SIZE)
            logger.debug(f"Got digest: {auth}.")

            length= struct.unpack("!I", await reader.read(4))[0]
            data = b""
            while len(data) < length:
                newdata = await reader.read(length - len(data))
                if len(newdata) == 0:
                    break
                data += newdata

            stomach = hmac.new(self.authkey.encode("UTF-8"), data, sha512)
            if not hmac.compare_digest(stomach.digest(), auth):
                writer.write(ERROR_HMAC)
                return

            logger.debug(f"Got message length: {length}, data: {data}.")
            try:
                logger.debug(f"Decoded: {data.decode('UTF-8')}")
                message: Dict[str, Any] = json.loads(data.decode("UTF-8"))
                logger.debug(f"Loaded: {message}")
                # Any of these will throw a KeyError with broken packets.
                message["type"], message["meta"], message["cont"]
            except:
                logger.exception("hrrm")
                writer.write(ERROR_PACK)
                return

            logger.debug(message)
            writer.write(ERROR_OK)

            await self.route(message)
        except:
            logger.exception("Got exception inside main commloop handler. Uh oh!")
            writer.write(ERROR_UNKNOWN)


    async def route(self, message: Dict[str, Any]):
        if message["type"] not in self.routing:
            logger.debug("No routing info for type")
            return

        handler = None  # type: MCommEvent

        for module in self.master.modules.values():
            for p_handler in filter(lambda x: isinstance(x, MCommEvent), module.handlers.values()):
                if p_handler.name == message["type"]:
                    handler = p_handler
                    break

        if handler is None:
            logger.error(f"Found routing information for nonexistant handler \"{message['type']}\".")
            return

        channel_ids = self.routing[message["type"]].get(message["meta"], [])  # type: List[int]
        if len(channel_ids) == 0:
            logger.debug("Got message without ability to find routing info. Ignoring.")
            return

        channels = [x for x in self.master.iter_channels() if x.id in channel_ids]

        for channel in channels:
            try:
                await handler.execute(channel, message["cont"])
            except:
                logger.exception("Caught exception inside commloop event handler.")


def comm_event(name):
    def inner(function: Callable[[MChannel, Any], Awaitable[None]]):
        from .master import master
        event = MCommEvent(name, function.__module__, function)
        event.register(master)

    return inner


class MCommEvent(MHandler):
    def __init__(self,
                 name: str,
                 module: str,
                 func: Callable[[MChannel, Any], Awaitable[None]]):

        super().__init__(name, module)

        self.func = func

    async def execute(self, channel: MChannel, message: Any):
        await self.func(channel, message)
