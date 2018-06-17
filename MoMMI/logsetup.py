# Handles setup of the loggers.

import logging
import logging.handlers
import re
import copy
from pathlib import Path
from typing import cast, Type

COLOR_ESCAPE = re.compile(r"\$(BLACK|RED|GREEN|YELLOW|BLUE|MAGENTA|CYAN|WHITE|BOLD|RESET)")

class NotColorFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        record = copy.copy(record)
        if isinstance(record.msg, str):
            record.msg = COLOR_ESCAPE.sub("", record.msg)
        return super().format(record)

ColorFormatter: Type[logging.Formatter]

try:
    import colorama

    RESET = colorama.Style.RESET_ALL
    BOLD = colorama.Style.BRIGHT
    BLACK = colorama.Fore.BLACK
    RED = colorama.Fore.RED
    GREEN = colorama.Fore.GREEN
    YELLOW = colorama.Fore.YELLOW
    BLUE = colorama.Fore.BLUE
    MAGENTA = colorama.Fore.MAGENTA
    CYAN = colorama.Fore.CYAN
    WHITE = colorama.Fore.WHITE
    LEVELNAME_COLORS = {
        "WARNING": YELLOW,
        "INFO": WHITE,
        "DEBUG": BLUE,
        "CRITICAL": RED,
        "ERROR": RED
    }

    colorama.init()

    class __ColorFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            record = copy.copy(record)
            if record.levelname in LEVELNAME_COLORS:
                record.levelname = LEVELNAME_COLORS[record.levelname] + record.levelname + RESET

            record.name = f"{GREEN}{record.name}{RESET}"
            if isinstance(record.msg, str):
                record.msg = COLOR_ESCAPE.sub(lambda x: cast(str, globals()[x.group(1)]), record.msg) + RESET

            return super().format(record)

    ColorFormatter = __ColorFormatter

except ImportError:
    ColorFormatter = NotColorFormatter

def setup_logs() -> None:
    outdir = Path("logs")
    if not outdir.is_dir():
        outdir.mkdir(parents=True)

    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)

    colorformatter = ColorFormatter("[%(levelname)s] %(name)s: %(message)s")
    formatter = NotColorFormatter("[%(levelname)s] %(name)s: %(message)s")

    # StreamHandler for console output.
    handler: logging.Handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(colorformatter)
    logger.addHandler(handler)

    # FileHandler to log EVERYTHING.
    path = outdir/"all.log"
    open(path, "a").close()

    handler = logging.FileHandler(str(path))
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # FileHandler to log errors.
    path = outdir/"error.log"
    open(path, "a").close()

    handler = logging.FileHandler(str(path))
    handler.setLevel(logging.ERROR)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    path = outdir/"chat.log"
    open(path, "a").close()

    handler = logging.FileHandler(str(path))
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter())
    chatlogger = logging.getLogger("chat")
    chatlogger.propagate = False
    chatlogger.addHandler(handler)

    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("bottom").setLevel(logging.WARNING)
    logging.getLogger("github3").setLevel(logging.WARNING)
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.INFO)
