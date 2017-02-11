# Handles setup of the loggers.

import logging
import logging.handlers
import os.path
import os

outdir = "logs"
if not os.path.isdir(outdir):
    os.mkdir(outdir)

logger = logging.getLogger()
logger.setLevel(logging.NOTSET)

formatter = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")

# StreamHandler for console output.
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(formatter)
logger.addHandler(handler)


# FileHandler to log EVERYTHING.
path = os.path.join(outdir, "all.log")
try:
    open(path, "a").close()

    handler = logging.FileHandler(path)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

except:
    logging.exception(f"Unable to create ALL log handler for file {path}.")


# FileHandler to log errors.
path = os.path.join(outdir, "error.log")
try:
    open(path, "a").close()

    handler = logging.FileHandler(path)
    handler.setLevel(logging.ERROR)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

except:
    logging.exception(f"Unable to create ERROR log handler for file {path}.")


path = os.path.join(outdir, "chat.log")
try:
    open(path, "a").close()

    handler = logging.FileHandler(path)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter())
    chatlogger = logging.getLogger("chat")
    chatlogger.propogate = False
    chatlogger.addHandler(handler)

except:
    logging.exception(f"Unable to create CHAT log handler for file {path}.")


logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("bottom").setLevel(logging.WARNING)
logging.getLogger("github3").setLevel(logging.WARNING)
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.INFO)
