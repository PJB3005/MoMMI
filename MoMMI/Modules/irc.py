"""

from typing import List
from ..commands import unsafe_always_command, command, command_help
from ..util import output, getrole
from ..config import get_config
from ..client import client
from ..permissions import isbanned, bantypes
import logging
import asyncio
import bottom
import re
"""
import logging
import bottom
import re
import asyncio
from discord import Server, Member, Message
from MoMMI.handler import MHandler
from MoMMI.master import master
from MoMMI.commands import always_command

# List of messages relayed to IRC. Prevent getting kicked for repeated messages.
# TODO: Move to temp storage.
last_messages = [None] * 3  # type: List[str]

class MIrcTransform(MHandler):
    def __init__(self, name, module, func):
        super().__init__(name, module)

        self.func = func

    async def transform(self, message, author, irc_client, discord_server):
        return await self.func(message, author, irc_client, discord_server)


class MDiscordTransform(MHandler):
    def __init__(self, name, module, func):
        super().__init__(name, module)

        self.func = func

    async def transform(self, message, author, discord_server, irc_client):
        return await self.func(message, author, discord_server, irc_client)

# Functions that do message modification before sending to IRC
# Take message, author, discord server, irc client
def irc_transform(name):
    def inner(function):
        handler = MIrcTransform(name, function.__module__, function)
        handler.register(master)

    return inner

# Functions that do message modification before sending to Discord
# Take message, author, irc client, discord server
def discord_transform(name):
    def inner(function):
        handler = MDiscordTransform(name, function.__module__, function)
        handler.register(master)

    return inner

"""
irc_client = irc_client = bottom.Client(
    host=get_config("mainserver.irc.irc.address"),
    port=get_config("mainserver.irc.irc.port"),
    loop=asyncio.get_event_loop(),
    ssl=True
)
"""

logger = logging.getLogger(__name__)
messagelogger = logging.getLogger("IRC")
MENTION_RE = re.compile(r"<@!?(\d+)>")
ROLE_RE = re.compile(r"<@&(\d+)>")
CHANNEL_RE = re.compile(r"<#(\d+)>")
EMOJI_RE = re.compile(r"<:(.+):(\d+)>")
IRC_MENTION_RE = re.compile(r"@([^@]+?)@")
IGNORED_NAMES = {"travis-ci", "vg-bot", "py-ctcp"}

class IrcConnection:
    def __init__(self, name):
        logger.info(f"Creating IrcConnection for server {name}.")
        config = master.config.modules["irc"]["servers"][name]

        self.name = name
        self.address = config["address"]
        self.port = config["port"]

        self.username = config["user"]["name"]
        self.realname = config["user"]["realname"]
        self.nick = config["user"]["nick"]

        self.channels = []
        for server in master.config.servers["servers"]:
            if server.get("modules") and server["modules"].get("irc"):
                cfg = server["modules"]["irc"]
                for channel in cfg:
                    if channel["server"] != self.name:
                        continue

                    logger.info(f"Registered {channel['irc_channel']} <-> {channel['discord_channel']} for IRC relaying.")
                    self.channels.append((channel["irc_channel"], channel["discord_channel"]))

        self.client = bottom.Client(
            host=self.address,
            port=self.port,
            loop=asyncio.get_event_loop(),
            ssl=True
        )

        @self.client.on("client_connect")
        async def connect(**kwargs):
            logger.info(f"Connected to IRC server {self.name}.")
            self.client.send("NICK", nick=self.nick)
            self.client.send("USER", user=self.username, realname=self.realname)

            done, pending = await asyncio.wait(
                [self.client.wait("RPL_ENDOFMOTD"),
                 self.client.wait("ERR_NOMOTD")],
                loop=self.client.loop,
                return_when=asyncio.FIRST_COMPLETED
            )

            for future in pending:
                future.cancel()

            for channel, discord in self.channels:
                self.client.send('JOIN', channel=channel)

        @self.client.on('PING')
        def keepalive(message, **kwargs):
            self.client.send('PONG', message=message)

        @self.client.on("PRIVMSG")
        async def message(nick, target, message, **kvargs):
            if nick in IGNORED_NAMES:
                return

            # fuck me
            discord_target = None
            for channel, discord in self.channels:
                if channel == target:
                    for server in master.servers.values():
                        if discord in server.channels:
                            discord_target = server.channels[discord]
                            break

            messagelogger.info(message)

            for handler in discord_target.iter_handlers(MDiscordTransform):
                message = await handler.transform(message, nick, discord_target.server, self.client)

            await discord_target.send("\u200B**IRC:** `<{}>` {}".format(nick, message))


        asyncio.ensure_future(self.client.connect(), loop=self.client.loop)

async def load(loop=None):
    if master.cache.get("irc_client_list") is not None:
        return

    cache = {}
    servers = master.config.get_module("irc", "servers")
    if servers is not None:
        for name in servers.keys():
            cache[name] = IrcConnection(name)

    master.set_cache("irc_client_list", cache)

async def unload(loop=None):
    if not master.has_cache("irc_client_list"):
        return

    logger.info("Dropping IRC connection.")
    for connection in master.get_cache("irc_client_list").values():
        await connection.client.disconnect()

    master.del_cache("irc_client_list")

@always_command("irc_relay", unsafe=True)
async def ircrelay(channel, match, message: Message):
    #if isbanned(message.author, bantypes.irc):
    #    return

    content = message.content
    for attachment in message.attachments:
        content += " " + attachment["url"]

    if len(content) == 0 or content[0] == "\u200B":
        return

    target_connection = None
    target_channel = None
    for connection in channel.server.master.cache["irc_client_list"].values():
        for irc_channel, discord_channel in connection.channels:
            if channel.id == discord_channel:
                target_channel = irc_channel
                target_connection = connection
                break


    if target_connection is None:
        return



    for handler in channel.iter_handlers(MIrcTransform):
        content = await handler.transform(content, message.author, target_connection.client, message.server)

    # Insert a zero-width space so people with the same name on IRC don't get pinged.
    author = prevent_ping(message.author.name)

    try:
        for split_message in content.split("\n"):
            # Yes, I could use a loop.
            # Know what a loop would do? Bloat this line count way too bloody much.
            if split_message == last_messages[0] == last_messages[1] == last_messages[2]:
                return

            last_messages.pop(0)
            last_messages.append(split_message)

            target_connection.client.send("PRIVMSG", target=target_channel, message="<{}> {}".format(author, split_message))

    except RuntimeError:
        pass

"""
@command_help("irc", "Commands for interacting with IRC.", "irc who")
@command("irc who")
async def irc_command(content, match, message):
    """


def prevent_ping(name: str):
    return name[:1] + "\u200B" + name[1:]


@irc_transform("convert_disc_mention")
async def convert_disc_mention(message, author, irc_client, discord_server):
    try:
        return MENTION_RE.sub(lambda match: "@{}".format(prevent_ping(discord_server.get_member(match.group(1)).name)), message)
    except:
        return message


@irc_transform("convert_disc_channel")
async def convert_disc_channel(message, author, irc_client, discord_server: Server):
    try:
        return CHANNEL_RE.sub(lambda match: "#{}".format(discord_server.get_channel(match.group(1)).name), message)

    except:
        return message


@irc_transform("convert_role_mention")
async def convert_role_mention(message, author, irc_client, discord_server: Server):
    try:
        return ROLE_RE.sub(lambda match: "@{}".format(getrole(discord_server, match.group(1)).name), message)

    except:
        return message


@irc_transform("convert_custom_emoji")
async def convert_custom_emoji(message, author, irc_client, discord_server: Server):
    try:
        return EMOJI_RE.sub(lambda match: ":{}:".format(match.group(1)), message)

    except:
        return message


@discord_transform("convert_irc_mention")
async def convert_irc_mention(message, author, discord_server, irc_client):
    #print("hrm?")
    try:
        return IRC_MENTION_RE.sub(lambda match: "<@{}>".format(discord_server.get_server().get_member_named(match.group(1)).id), message)
    except:
        return message
