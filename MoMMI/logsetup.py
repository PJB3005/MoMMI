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
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)


# FileHandler to log EVERYTHING.
path = os.path.join(outdir, "all.log")
try:
    open(path, "a").close()

    handler = logging.FileHandler(path)
    handler.setLevel(logging.INFO) # Discord.py makes DEBUG logs useless.
    handler.setFormatter(formatter)
    logger.addHandler(handler)

except Exception as e:
    logging.exception("Unable to create ALL log handler for file %s.", path)


# FileHandler to log errors.
path = os.path.join(outdir, "error.log")
try:
    open(path, "a").close()

    handler = logging.FileHandler(path)
    handler.setLevel(logging.ERROR)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

except Exception as e:
    logging.exception("Unable to create ERROR log handler for file %s.", path)

