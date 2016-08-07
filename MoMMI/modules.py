from .client import client
from .config import config
import asyncio
import logging
import os
import os.path
import importlib

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

def reload_modules():
    count = 0
    errored = 0
    new = 0
    filenames = []

    for module in modules:
        if hasattr(module, "unload"):
            try:
                module.unload()

            except:
                logger.exception("Exception while unloading a module.")

        try:
            filenames.append(module.__file__)
            importlib.reload(module)
            count += 1
        except:
            logger.exception("Exception while trying to reload a module.")
            errored += 1
    
    directory = os.path.join("MoMMI", "Modules")
    for file in os.listdir(directory):
        path = os.path.join(directory, file)
        if os.path.isfile(path) and file[-3:] == ".py" and file != "__init__.py":
            if os.path.abspath(path) in filenames:
                continue

            logger.info("Loading NEW module %s", path)
            try:
                modules.append(importlib.import_module("MoMMI.Modules.%s" % (file[:-3])))
                new += 1

            except:
                logger.exception("Error while loading NEW module %s", path)

    return count, errored, new
    