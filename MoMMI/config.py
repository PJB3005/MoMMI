import logging
import yaml
import asyncio
import aiofiles

logger = logging.getLogger("config")
config = {}

async def parse(filename, safe=False):
    global config
    f = await aiofiles.open(filename, mode='r')
    try:
        document = await f.read()
    finally:
        f.close()


    try:   
        if safe:
            config = yaml.safe_load(document)
        else:
            config = yaml.load(document)

    except Exception as e:
        logger.exception("Failed to load config file %s due to exception.")
        return

def get_config(value, default=None):
    tree = value.split(".")

    current = config
    for node in tree:
        if type(current) == dict and node in current:
            current = current[node]
        
        else:
            current = default
            break

    return current

logger.info("Doing initial config file load.")
loop = asyncio.get_event_loop()

# TODO: Unhardcode base config file, somehow, probably argparse.
loop.run_until_complete(parse("config.yml"))
logger.info("Successfully loaded config.yml.")
logger.debug("Config is %s" % (config))

