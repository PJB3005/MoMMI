import logging
import yaml
import asyncio
import aiofiles

logger = logging.getLogger("config")
config = {}
overrides = {}

async def parse(filename, safe=False, override=False):
    global config
    global overrides
    try:
        f = await aiofiles.open(filename, mode='r')
        try:
            document = await f.read()
        finally:
            f.close()

        out = None
        if safe:
            out = yaml.safe_load(document)
        else:
            out = yaml.load(document)

        if override:
            overrides = out
        else:
            config = out

    except Exception as e:
        logger.exception("Failed to load config file %s due to exception.")
        return

def get_config(value, default=None, dictionary=None):
    logger.info(dictionary)
    if dictionary == None:
        logger.info("yes")
        override = get_config(value, None, overrides)
        if override:
            return override
        dictionary = config

    tree = value.split(".")

    current = dictionary
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
loop.run_until_complete(parse("override.yml", override=True))
logger.info("Successfully loaded config.yml.")
logger.debug("Config is %s" % (config))

