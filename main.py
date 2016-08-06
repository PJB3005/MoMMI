import logging
# Here so other imports already get logged properly.
logging.basicConfig(filename="example.log", level=logging.DEBUG)
import aioprocessing.connection
import asyncio
import discord
from MoMMI.config import config


client = discord.Client()

@client.async_event
def on_ready():
    logging.info("Logged in as")
    logging.info(client.user.name)
    logging.info(client.user.id)
    logging.info("Connected servers:")
    for server in client.servers:
        logging.info(server.name)

    logging.info("------")

if config["token"] == "unset":
    logging.critical("Discord auth token is unset, aborting.")
    exit()

logging.debug("Starting client.")
client.run(config["token"])