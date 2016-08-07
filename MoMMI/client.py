# Houses the main client object.

import discord
import logging


client = discord.Client()
logger = logging.getLogger(__name__)

@client.event
async def on_ready():
    from . import modules
    logger.info("Logged in as %s (%s)", client.user.name, client.user.id)
    logger.info("Connected servers:")
    for server in client.servers:
        logger.info("    %s", server.name)

    logger.info("Loaded %s commands", len(modules.commands))
    modules.setup_modules()

@client.event
async def on_error(event, *args, **kwargs):
    logger.exception("Caught exception inside client event.")