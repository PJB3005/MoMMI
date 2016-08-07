import sys
import logging


logger = logging.getLogger(__name__)

def excepthook(exctype, value, traceback):
    logger.exception(value)

sys.excepthook = excepthook