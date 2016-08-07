import asyncio
import logging
from aioprocessing.connection import AioListener as Listener
from ..config import config


httpcomm = config.get("httpcomm", {})

address = ("localhost", httpcomm.get("port", 1679))
authkey = httpcomm.get("authkey", "UNSET!!!").encode("utf-8")


logger = logging.getLogger(__name__)
server = Listener(address)
processing = True

async def process_loop():
    logger.info("Starting commloop")
    while processing:
        conn = await server.coro_accept()
        logger.info("Received connection from client %s.", server.last_accepted)
        while True: # While we have a connection
            try:
                msg = await conn.coro_recv()
                logger.info("Received a message from the client: %s", msg)

            # EOFError gets thrown when the connection gets closed by the client.
            except EOFError as eof:
                logger.info("Dropping connection.")
                break

logger.info("test")
asyncio.ensure_future(process_loop())