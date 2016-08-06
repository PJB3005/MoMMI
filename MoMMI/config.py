import logging
import yaml
import asyncio
import aiofiles


config = {}

@asyncio.coroutine
def parse(filename, safe=False):
    global config
    f = yield from aiofiles.open(filename, mode='r')
    try:
        document = yield from f.read()
    finally:
        f.close()
     
    try:   
        if safe:
            config = yaml.safe_load(document)
        else:
            config = yaml.load(document)

    except Exception as e:
        logging.exception("Failed to load config file %s due to exception.")
        return

logging.info("Doing initial config file load.")
loop = asyncio.get_event_loop()

# TODO: Unhardcode base config file, somehow, probably argparse.
loop.run_until_complete(parse("config.yml"))
logging.info("Successfully loaded config.yml.")
logging.info("Config is %s" % (config))

