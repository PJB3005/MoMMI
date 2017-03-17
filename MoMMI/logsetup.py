# Handles setup of the loggers.

import logging
import logging.handlers
import os.path
import os
import re
import copy

outdir = "logs"
if not os.path.isdir(outdir):
    os.mkdir(outdir)

logger = logging.getLogger()
logger.setLevel(logging.NOTSET)

RESET = "\033[0m"
BOLD = "\033[1m"
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = (f"\033[1;{x}m" for x in range(30, 38))
LEVELNAME_COLORS = {
    "WARNING": YELLOW,
    "INFO": WHITE,
    "DEBUG": BLUE,
    "CRITICAL": RED,
    "ERROR": RED
}
COLOR_ESCAPE = re.compile(r"\$(BLACK|RED|GREEN|YELLOW|BLUE|MAGENTA|CYAN|WHITE|BOLD|RESET)")

class ColorFormatter(logging.Formatter):
    def format(self, record):
        record = copy.copy(record)
        if record.levelname in LEVELNAME_COLORS:
            record.levelname = LEVELNAME_COLORS[record.levelname] + record.levelname + RESET

        record.name = f"{GREEN}{record.name}{RESET}"
        if isinstance(record.msg, str):
            record.msg = COLOR_ESCAPE.sub(lambda x: globals()[x.group(1)], record.msg) + RESET

        return super().format(record)

class NotColorFormatter(logging.Formatter):
    def format(self, record):
        record = copy.copy(record)
        if isinstance(record.msg, str):
            record.msg = COLOR_ESCAPE.sub("", record.msg)
        return super().format(record)

colorformatter = ColorFormatter("[%(levelname)s] %(name)s: %(message)s")
formatter = NotColorFormatter("[%(levelname)s] %(name)s: %(message)s")

# StreamHandler for console output.
handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(colorformatter)
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
