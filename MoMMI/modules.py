from .client import client
from .config import config
import asyncio
import logging
import os
import os.path
import importlib
import signal
import sys


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
                mod = importlib.import_module("MoMMI.Modules.%s" % (file[:-3]))
                if hasattr(mod, "load"):
                    await mod.load()

                modules.append(mod)
                count += 1

            except:
                logger.exception("Error while loading module %s", path)

    return count


async def reload_modules():
    count = 0
    errored = 0
    new = 0
    filenames = []

    for module in modules:
        if hasattr(module, "unload"):
            try:
                await module.unload(loop=None)

            except:
                logger.exception("Exception while unloading a module.")

        try:
            filenames.append(module.__file__)
            importlib.reload(module)
            count += 1

        except:
            logger.exception("Exception while trying to reload a module.")
            errored += 1

    for module in modules:
        try:
            if hasattr(module, "load"):
                await module.load()
        except:
            logger.exception("Hit error while doing load() callback on module %s" % module.__name__)

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


# Sanely unload modules!
def handle_signterm(signum, frame):
    logger.info("SIGTERM received, unloading modules and shutting down!")
    loop = asyncio.get_event_loop()
    tasks = [asyncio.ensure_future(module.unload(loop=loop), loop=loop) for module in modules if hasattr(module, "unload")]
    logger.info(tasks)
    loop.stop()
    loop.run_until_complete(asyncio.gather(*tasks))
    logger.info("ded")
    sys.exit()
    loop.run_until_complete(client.logout())
    loop.close()
    logger.info("huh")

# Fucking hell I wiped the databases AGAIN.
# signal.signal(signal.SIGTERM, handle_signterm)
