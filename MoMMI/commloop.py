import asyncio
import asyncio.streams
import hmac
import json
import logging
import struct
from hashlib import sha512
from typing import Dict, Tuple, Any
from .config import get_config

DIGEST_SIZE = sha512().digest_size

ERROR_OK = struct.pack("!B", 0)
ERROR_ID = struct.pack("!B", 1)
ERROR_PACK = struct.pack("!B", 2)
ERROR_HMAC = struct.pack("!B", 3)

ADDRESS: str = get_config("commloop.address", "localhost")
PORT: int = get_config("commloop.port", 1679)
AUTHKEY: str = get_config("commloop.auth", "UNSET!!!").encode("utf-8")

logger = logging.getLogger(__name__)
connection = None
processing = True
events = []


class commloop(object):
    def __init__(self):
        self.server: asyncio.Server = None
        self.clients: Dict[asyncio.Task, Tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}

    async def start(self, loop: asyncio.AbstractEventLoop):
        self.server = await asyncio.start_server(self.accept_client,
                                                 ADDRESS,
                                                 PORT,
                                                 loop=loop)
        logger.info("Started the commloop server.")

    def accept_client(self, client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter):
        logger.info("Accepting new client!")
        task: asyncio.Task = asyncio.Task(self.handle_client(client_reader, client_writer))
        self.clients[task] = (client_reader, client_writer)

        def client_done(task):
            logger.info("Dropping client connection.")
            del self.clients[task]

        task.add_done_callback(client_done)

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        data: bytes = await reader.read(2)  # Read ID.
        if data != b"\x30\x05":
            writer.write(ERROR_ID)
            return

        logger.info(f"Got ID packets: {data}.")

        auth: bytes = await reader.read(DIGEST_SIZE)
        logger.info(f"Got digest: {auth}.")

        length: int = struct.unpack("!I", await reader.read(4))[0]
        data = b""
        while len(data) < length:
            newdata = await reader.read(length - len(data))
            if len(newdata) == 0:
                break
            data += newdata
        logger.info(f"Got message ength: {length}, data: {data}.")
        try:
            logger.info(f"Decoded: {data.decode('UTF-8')}")
            message: Dict[str, Any] = json.loads(data.decode("UTF-8"))
            logger.info(f"Loaded: {message}")
            # Any of these will throw a KeyError with broken packets.
            message["type"], message["meta"], message["cont"]
        except:
            logger.exception("hrrm")
            writer.write(ERROR_PACK)
            return

        stomach: hmac.HMAC = hmac.new(AUTHKEY, data, sha512)
        if not hmac.compare_digest(stomach.digest(), auth):
            writer.write(ERROR_HMAC)
            return

        logger.info(message)
        writer.write(ERROR_OK)

        for event in events:
            try:
                await event(message)
            except:
                logger.exception("Caught exception inside commloop event handler.")


def comm_event(function):
    global events
    if not asyncio.iscoroutinefunction(function):
        logger.warning("Attempted to register non-coroutine %s as comm_event!", function)
        function = asyncio.coroutine(function)

    events.append(function)
    return function

loop = commloop()
event_loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()
asyncio.ensure_future(loop.start(event_loop))
