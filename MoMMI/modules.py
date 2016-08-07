from .client import client
from .config import config
import asyncio
import logging
import os
import os.path
import importlib
import MoMMI.Modules.commloop

logger = logging.getLogger(__name__)
modules = []

async def load_modules():
    count = 0

    directory = config.get("moduledir", os.path.join("MoMMI", "Modules"))
    for file in os.listdir(directory):
        path = os.path.join(directory, file)
        if os.path.isfile(path) and file[-3:] == ".py" and file != "__init__.py":
            logger.info("Loading module %s", path)
            
            try:
                modules.append(importlib.import_module("MoMMI.Modules.%s" % (file[:-3])))
                count += 1

            except:
                logger.exception("Error while loading module %s", path)

    return count