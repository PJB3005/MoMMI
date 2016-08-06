#!/usr/bin/env python3.5

import asyncio
import MoMMI.logging
from MoMMI.config import config
import logging
import aioprocessing.connection
import discord


client = discord.Client()
logger = logging.getLogger("main")

@client.async_event
def on_ready():
    logger.info("Logged in as")
    logger.info(client.user.name)
    logger.info(client.user.id)
    logger.info("Connected servers:")
    for server in client.servers:
        logger.info("    %s", server.name)

    logger.info("------")

if config["token"] == "unset":
    logger.critical("Discord auth token is unset, aborting.")
    exit()

logger.info("Starting client.")
client.run(config["token"])