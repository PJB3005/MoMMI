import aioprocessing.connection
import asyncio
import discord
import logging

logging.basicConfig(filename="example.log", level=logging.DEBUG)
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

logging.debug("Starting client.")
client.run("test")