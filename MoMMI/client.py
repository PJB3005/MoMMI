# Houses the main client object.

import discord
import logging


logger = logging.getLogger(__name__)
client = discord.Client()

@client.event
async def on_ready():
    logger.info("Logged in as %s (%s)", client.user.name, client.user.id)
    logger.info("Connected servers:")
    for server in client.servers:
        logger.info("    %s", server.name)
