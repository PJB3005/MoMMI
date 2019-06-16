import logging
import re
import asyncio
from typing import Callable, List, Awaitable, Tuple, Any, Match, Dict, Optional
import bottom
from discord import User, Message
from MoMMI.handler import MHandler
from MoMMI.master import master
from MoMMI.server import MChannel
from MoMMI.commands import always_command
from MoMMI.types import SnowflakeID

# List of messages relayed to IRC. Prevent getting kicked for repeated messages.
# TODO: Move to temp storage.
last_messages: List[str] = [""] * 3

IrcTransformType = Callable[[str, User, bottom.Client, MChannel], Awaitable[str]]

# Functions that do message modification before sending to IRC
# Take message, author, discord server, irc client
def irc_transform(name: str) -> Callable[[IrcTransformType], None]:
    def inner(function: IrcTransformType) -> None:
        handler = MIrcTransform(name, function.__module__, function)
        handler.register(master)

    return inner

class MIrcTransform(MHandler):
    def __init__(self, name: str, module: str, func: IrcTransformType) -> None:
        super().__init__(name, module)

        self.func: IrcTransformType = func

    async def transform(self, message: str, author: User, irc_client: bottom.Client, discord_server: MChannel) -> str:
        return await self.func(message, author, irc_client, discord_server)

DiscordTransformType = Callable[[str, str, MChannel, bottom.Client], Awaitable[str]]

# Functions that do message modification before sending to Discord
# Take message, author, irc client, discord server
def discord_transform(name: str) -> Callable[[DiscordTransformType], None]:
    def inner(function: DiscordTransformType) -> None:
        handler = MDiscordTransform(name, function.__module__, function)
        handler.register(master)

    return inner

class MDiscordTransform(MHandler):
    def __init__(self, name: str, module: str, func: DiscordTransformType) -> None:
        super().__init__(name, module)

        self.func: DiscordTransformType = func

    async def transform(self, message: str, author: str, discord_server: MChannel, irc_client: bottom.Client) -> str:
        return await self.func(message, author, discord_server, irc_client)

logger = logging.getLogger(__name__)
messagelogger = logging.getLogger("chat")
MENTION_RE = re.compile(r"<@!?(\d+)>")
ROLE_RE = re.compile(r"<@&(\d+)>")
CHANNEL_RE = re.compile(r"<#(\d+)>")
EMOJI_RE = re.compile(r"<:(.+):(\d+)>")
IRC_MENTION_RE = re.compile(r"@([^@]+?)@")
IGNORED_NAMES = {"travis-ci", "vg-bot", "py-ctcp"}

class IrcConnection:
    def __init__(self, name: str) -> None:
        logger.info(f"Creating IrcConnection for server {name}.")
        config = master.config.modules["irc"]["servers"][name]

        self.name: str = name
        self.address: str = config["address"]
        self.port: int = config["port"]

        self.username: str = config["user"]["name"]
        self.realname: str = config["user"]["realname"]
        self.nick: str = config["user"]["nick"]
        self.server_password: Optional[str] = config.get("password")

        self.channels: List[Tuple[str, SnowflakeID]] = []
        for server in master.config.servers["servers"]:
            if server.get("modules") and server["modules"].get("irc"):
                cfg = server["modules"]["irc"]
                for channel in cfg:
                    if channel["server"] != self.name:
                        continue

                    irc_name = channel['irc_channel']
                    discord_id = SnowflakeID(channel["discord_channel"])

                    logger.info(f"Registered {irc_name} <-> {discord_id} for IRC relaying.")
                    self.channels.append((irc_name, discord_id))

        self.client = bottom.Client(
            host=self.address,
            port=self.port,
            loop=asyncio.get_event_loop(),
            ssl=True
        )

        self.client.on("client_connect")(self.connect)
        self.client.on("PING")(self.keepalive)
        self.client.on("PRIVMSG")(self.message)

        asyncio.ensure_future(self.client.connect(), loop=self.client.loop)


    async def connect(self, **kwargs: Any) -> None:
        logger.info(f"Connected to IRC server {self.name}.")
        if self.server_password:
            self.client.send("PASS", password=self.server_password)

        self.client.send("NICK", nick=self.nick)
        self.client.send("USER", user=self.username, realname=self.realname)

        _: Any
        _, pending = await asyncio.wait(
            [self.client.wait("RPL_ENDOFMOTD"),
             self.client.wait("ERR_NOMOTD")],
            loop=self.client.loop,
            return_when=asyncio.FIRST_COMPLETED
        )

        for future in pending:
            future.cancel()

        for channel, _ in self.channels:
            self.client.send('JOIN', channel=channel)


    def keepalive(self, message: str, **kwargs: Any) -> None:
        self.client.send('PONG', message=message)


    async def message(self, nick: str, target: str, message: str, **kwargs: Any) -> None:
        from MoMMI.util import utcnow
        if nick in IGNORED_NAMES:
            return

        try:
            discord_target = self.get_discord_channel(target)
        except KeyError:
            # Channel we don't know about, probably a PM or something.
            return

        messagelogger.info(f"[{utcnow().isoformat()}](IRC {target}) {nick}: {message}")

        for handler in discord_target.iter_handlers(MDiscordTransform):
            message = await handler.transform(message, nick, discord_target, self.client)

        await discord_target.send("\u200B**IRC:** `<{}>` {}".format(nick, message))

    def get_discord_channel(self, irc: str) -> MChannel:
        """
        Fetches the Discord channel corresponding to an IRC channel.
        Raises KeyError if we don't know the IRC channel.
        """
        for channel, discord in self.channels:
            if channel == irc:
                for server in master.servers.values():
                    if discord in server.channels:
                        return server.channels[SnowflakeID(discord)]

        raise KeyError(f"Unknown IRC channel: '{irc}'")

async def load(loop: asyncio.AbstractEventLoop) -> None:
    if master.cache.get("irc_client_list") is not None:
        return

    cache = {}
    servers: Dict[str, Any] = master.config.get_module("irc.servers", {})
    if servers is not None:
        for name in servers.keys():
            cache[name] = IrcConnection(name)

    master.set_cache("irc_client_list", cache)

async def unload(loop: asyncio.AbstractEventLoop) -> None:
    if not master.has_cache("irc_client_list"):
        return

    logger.info("Dropping IRC connection.")
    for connection in master.get_cache("irc_client_list").values():
        await connection.client.disconnect()

    master.del_cache("irc_client_list")

@always_command("irc_relay", unsafe=True)
async def ircrelay(channel: MChannel, match: Match, message: Message) -> None:
    content = message.content
    for attachment in message.attachments:
        content += " " + attachment["url"]

    if not content or content[0] == "\u200B":
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
        content = await handler.transform(content, message.author, target_connection.client, channel)

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

            target_connection.client.send("PRIVMSG", target=target_channel, message="\x02<{}>\x02 {}".format(author, split_message))

    except RuntimeError:
        pass


def prevent_ping(name: str) -> str:
    return name[:1] + "\u200B" + name[1:]


@irc_transform("convert_discord_mention")
async def convert_disc_mention(message: str, author: User, irc_client: bottom.Client, channel: MChannel) -> str:
    try:
        def replace(match: Match) -> str:
            snowflake = SnowflakeID(match.group(1))
            member = channel.get_member(snowflake)
            name = prevent_ping(member.name)

            return f"@{name}"

        return MENTION_RE.sub(replace, message)

    except:
        return message


@irc_transform("convert_discord_channel")
async def convert_disc_channel(message: str, author: User, irc_client: bottom.Client, channel: MChannel) -> str:
    try:
        def replace(match: Match) -> str:
            snowflake = SnowflakeID(match.group(1))
            name = channel.server.get_channel(snowflake).name
            return f"#{name}"

        return CHANNEL_RE.sub(replace, message)

    except:
        return message


@irc_transform("convert_role_mention")
async def convert_role_mention(message: str, author: User, irc_client: bottom.Client, channel: MChannel) -> str:
    try:
        def replace(match: Match) -> str:
            snowflake = SnowflakeID(match.group(1))
            role = channel.get_role_snowflake(snowflake)
            return f"@{role.name}"

        return ROLE_RE.sub(replace, message)

    except:
        return message


@irc_transform("convert_custom_emoji")
async def convert_custom_emoji(message: str, author: User, irc_client: bottom.Client, channel: MChannel) -> str:
    try:
        def replace(match: Match) -> str:
            return ":{}:".format(match.group(1))

        return EMOJI_RE.sub(replace, message)

    except:
        return message


@discord_transform("convert_irc_mention")
async def convert_irc_mention(message: str, author: str, channel: MChannel, irc_client: bottom.Client) -> str:
    try:
        def replace(match: Match) -> str:
            return "<@{}>".format(channel.get_member_named(match.group(1)).id)

        return IRC_MENTION_RE.sub(replace, message)

    except:
        return message
