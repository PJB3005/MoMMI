# Houses the main client object.

import discord
import logging


client = discord.Client()  # Type: discord.Client
logger = logging.getLogger(__name__)
initial_module_load = True


@client.event
async def on_ready():
    global initial_module_load
    from . import modules
    from . import commands
    logger.info("Logged in as %s (%s)", client.user.name, client.user.id)
    logger.info("Connected servers:")
    commands.setup_commands()
    for server in client.servers:
        logger.info("    %s", server.name)

    if not initial_module_load:
        return

    initial_module_load = False
    count = await modules.load_modules()
    logger.info("Loaded %s modules.", count)


@client.event
async def on_error(event, *args, **kwargs):
    logger.exception("Caught exception inside client event.")
