from .commloop import comm_event
import logging


logger = logging.getLogger(__name__)

@comm_event
async def log(msg, address):
    logger.info("Received message from %s: %s", address, msg)
