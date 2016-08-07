from .commloop import comm_event
import logging


logger = logging.getLogger(__name__)

@comm_event
def github_event(msg, address):
    if msg["id"] == "github":
        logger.info("WEEE BOY GOT A MESSAGE FROM GITHUB: %s", msg)

