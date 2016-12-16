from ..commloop import comm_event
import logging

logger = logging.getLogger(__name__)


@comm_event
async def log(msg):
    logger.info(f"Received message: {msg}")
