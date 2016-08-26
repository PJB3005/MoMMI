import asyncio
import logging
from aioprocessing.connection import AioListener as Listener
from .config import get_config


address = get_config("commloop.address", "localhost"), get_config("commloop.port", 1679)
authkey = get_config("commloop.auth", "UNSET!!!").encode("utf-8")


logger = logging.getLogger(__name__)
server = Listener(address)
connection = None
processing = True
events = []

async def process_loop():
    logger.info("Starting commloop on address %s", address)
    while processing:
        connection = await server.coro_accept()
        logger.info("Received connection from client %s.", server.last_accepted)
        while True: # While we have a connection
            try:
                msg = await connection.coro_recv()
                for event in events:
                    try:
                        await event(msg, address)
                    except:
                        logger.exception("Caught exception inside commloop event handler.")

            # EOFError gets thrown when the connection gets closed by the client.
            except EOFError:
                logger.info("Dropping connection.")
                break


def comm_event(function):
    global events
    if not asyncio.iscoroutinefunction(function):
        logger.warning("Attempted to register non-coroutine %s as comm_event!", function)
        function = asyncio.coroutine(function)
    
    events.append(function)
    return function

processing_task = asyncio.ensure_future(process_loop())

def unload():
    global server
    processing_task.cancel()
    connection.close()
    server.close()
    del(server)