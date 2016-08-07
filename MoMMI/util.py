import logging


logger = logging.getLogger(__name__)

def getserver(client, name):
    for server in client.servers:
        logger.info(server.name)
        if server.name == name:
            return server

def getchannel(server, name):
    for channel in server.channels:
        logger.info(channel.name)
        if channel.name == name:
            return channel