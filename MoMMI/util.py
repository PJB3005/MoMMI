from .config import get_config
from .client import client
import re
import logging
import aiofiles
import pickle


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

def mainserver():
    return client.get_server(str(get_config("mainserver.id")))

async def output(channel, message):
    message = re.sub("@(everyone|here)", "@​\g<1>", message)
    await client.send_message(channel, message)

async def pickle_dump(object, filename):
    byte = pickle.dumps(obj)
    async with aiofiles.open(filename, "wb") as f:
        await f.write(byte)

async def pickle_load(filename):
    async with aiofiles.open(filename, "rb") as f:
        byte = await f.read()
    
    return pickle.loads(byte)
