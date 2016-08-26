import logging


logger = logging.getLogger(__name__)

def getserver(client, name):
    for server in client.servers:
        if server.name == name:
            return server

def getchannel(server, name):
    for channel in server.channels:
        if channel.name == name:
            return channel

def getrole(server, id):
    for role in server.roles:
        if role.id == id:
            return role