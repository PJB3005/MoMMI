import asyncio
import hmac
import json
import logging
import struct
from hashlib import sha512
from typing import Dict, Tuple, Any, Callable, Awaitable, Optional, List, Union
from MoMMI.channel import MChannel
from MoMMI.handler import MHandler
from MoMMI.server import MServer
from MoMMI.master import MoMMI
from MoMMI.types import SnowflakeID

DIGEST_SIZE = sha512().digest_size

ERROR_OK = struct.pack("!B", 0)
ERROR_ID = struct.pack("!B", 1)
ERROR_PACK = struct.pack("!B", 2)
ERROR_HMAC = struct.pack("!B", 3)
ERROR_UNKNOWN = struct.pack("!B", 4)

logger = logging.getLogger(__name__)


class commloop(object):
    def __init__(self, master: MoMMI, loop: asyncio.AbstractEventLoop) -> None:
        self.server: Optional[asyncio.AbstractServer] = None
        self.clients: Dict[asyncio.Future,
                           Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}

        self.master = master

        self.routing: Dict[str, Any] = master.config.get_main(
            "commloop.route", {})
        self.address: str = master.config.get_main(
            "commloop.address", "localhost")
        self.port: int = master.config.get_main("commloop.port", 1679)
        self.authkey: str = master.config.get_main("commloop.password")
        self.loop = loop

    async def start(self) -> None:
        self.server = await asyncio.start_server(
            self.accept_client,
            self.address,
            self.port,
            loop=self.loop
        )
        logger.debug("Started the commloop server.")

    async def stop(self) -> None:
        if self.server is None:
            raise RuntimeError("Server is none!")

        self.server.close()
        await self.server.wait_closed()

    def accept_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
        # logger.debug("Accepting new client!")
        task = asyncio.ensure_future(
            self.handle_client(client_reader, client_writer), loop=self.loop)
        self.clients[task] = (client_reader, client_writer)

        def client_done(task: asyncio.Future) -> None:
            # logger.debug("Dropping client connection.")
            del self.clients[task]

        task.add_done_callback(client_done)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            # Read ID.
            data = await reader.read(2)
            if data != b"\x30\x05":
                writer.write(ERROR_ID)
                return

            auth = await reader.read(DIGEST_SIZE)

            length = struct.unpack("!I", await reader.read(4))[0]
            data = b""
            while len(data) < length:
                newdata = await reader.read(length - len(data))
                if not newdata:
                    break
                data += newdata

            stomach = hmac.new(self.authkey.encode("UTF-8"), data, sha512)
            if not hmac.compare_digest(stomach.digest(), auth):
                writer.write(ERROR_HMAC)
                return

            try:
                message: Dict[str, Any] = json.loads(data.decode("UTF-8"))

            except:
                writer.write(ERROR_PACK)
                return

            if "type" not in message or "meta" not in message or "cont" not in message:
                writer.write(ERROR_PACK)
                return

            writer.write(ERROR_OK)

            await self.route(message)

        except:
            logger.exception(
                "Got exception inside main commloop handler. Uh oh!")
            writer.write(ERROR_UNKNOWN)

    async def route(self, message: Dict[str, Any]) -> None:
        # Do global comm events first.
        for globalhandler in self.master.iter_global_handlers(MGlobalCommEvent):
            await globalhandler.execute(message["cont"], message["meta"])

        if message["type"] not in self.routing:
            logger.warning(
                f"No routing info for type '$YELLOW{message['type']}$RESET'")
            return

        handler: Optional[MCommEvent] = None

        for module in self.master.modules.values():
            for p_handler in module.handlers.values():
                if isinstance(p_handler, MCommEvent) and p_handler.name == message["type"]:
                    handler = p_handler
                    break

        if handler is None:
            logger.error(
                f"Found routing information for nonexistant handler \"{message['type']}\".")
            return

        channels = self.routing[message["type"]].get(message["meta"])
        if not channels:
            logger.warning(
                f"Got message with unconfigured meta '{message['meta']}'")
            return

        for channelpair in channels:
            servername = verify_tabled_id(channelpair[0])
            channelname = verify_tabled_id(channelpair[1])

            server: MServer = self.master.get_server(servername)
            channel = server.get_channel(channelname)
            try:
                await handler.execute(channel, message["cont"], message["meta"])
            except:
                logger.exception(
                    "Caught exception inside commloop event handler.")


def verify_tabled_id(idname: Any) -> Union[str, SnowflakeID]:
    if isinstance(idname, int):
        return SnowflakeID(idname)

    elif isinstance(idname, str):
        return idname

    return SnowflakeID(0)


CommEventType = Callable[[MChannel, Any, str], Awaitable[None]]


def comm_event(name: str) -> Callable[[CommEventType], None]:
    def inner(function: CommEventType) -> None:
        from MoMMI.master import master
        event = MCommEvent(name, function.__module__, function)
        event.register(master)

    return inner


class MCommEvent(MHandler):
    def __init__(self,
                 name: str,
                 module: str,
                 func: CommEventType) -> None:

        super().__init__(name, module)

        self.func: CommEventType = func

    async def execute(self, channel: MChannel, message: Any, meta: str) -> None:
        await self.func(channel, message, meta)


GlobalCommEventType = Callable[[Any, str], Awaitable[None]]


def global_comm_event(name: str) -> Callable[[GlobalCommEventType], None]:
    def inner(function: GlobalCommEventType) -> None:
        from MoMMI.master import master
        event = MGlobalCommEvent(name, function.__module__, function)
        event.register(master)

    return inner


class MGlobalCommEvent(MHandler):
    def __init__(self,
                 name: str,
                 module: str,
                 func: GlobalCommEventType) -> None:

        super().__init__(name, module)

        self.func: GlobalCommEventType = func

    async def execute(self, message: Any, meta: str) -> None:
        await self.func(message, meta)
