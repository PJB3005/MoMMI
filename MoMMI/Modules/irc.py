from discord import Server, Member
from ..commands import unsafe_always_command, command, command_help
from ..util import output
from ..config import get_config
from ..client import client
from ..permissions import isbanned, bantypes
import logging
import asyncio
import bottom
import re

# Functions that do message modification before sending to IRC
# Take message, author, discord server, irc client
irc_transforms = []

def irc_transform(func):
    irc_transforms.append(func)
    return func

# Functions that do message modification before sending to Discord
# Take message, author, irc client, discord server
discord_transforms = []

def discord_transform(func):
    discord_transforms.append(func)
    return func

irc_client = irc_client = bottom.Client(
    host=get_config("mainserver.irc.irc.address"),
    port=get_config("mainserver.irc.irc.port"),
    loop=asyncio.get_event_loop(),
    ssl=True
)
logger = logging.getLogger(__name__)
messagelogger = logging.getLogger("IRC")
MENTION_RE = re.compile(r"<@!?(\d+)>")
IRC_MENTION_RE = re.compile(r"@([^@]+?)@")
IGNORED_NAMES = {"travis-ci", "vg-bot", "py-ctcp"}


async def unload(loop=None):
    logger.info("Dropping IRC connection.")
    await irc_client.disconnect()


@irc_client.on("client_connect")
async def connect(**kwargs):
    logger.info("Connected")
    irc_client.send("NICK", nick=get_config("mainserver.irc.irc.user.nick"))
    irc_client.send("USER", user=get_config("mainserver.irc.irc.user.name"), realname=get_config("mainserver.irc.irc.user.realname"))
    irc_client.send('JOIN', channel=get_config("mainserver.irc.irc.channel"))

asyncio.ensure_future(irc_client.connect(), loop=irc_client.loop)


@irc_client.on("PRIVMSG")
async def message(nick, target, message, **kvargs):
    if nick in IGNORED_NAMES:
        return

    messagelogger.info(message)
    channel = client.get_channel(str(get_config("mainserver.irc.discord.channel")))

    content = message

    for func in discord_transforms:
        content = func(content, nick, channel.server, irc_client)

    await output(channel, "\u200B**IRC:** `<{}>` {}".format(nick, content))


@irc_client.on('PING')
def keepalive(message, **kwargs):
    irc_client.send('PONG', message=message)


@unsafe_always_command()
async def ircrelay(message):
    if isbanned(message.author, bantypes.irc):
        return

    if len(message.content) == 0 or message.content[0] == "\u200B" or message.channel.id != str(get_config("mainserver.irc.discord.channel")):
        return

    content = message.content

    for func in irc_transforms:
        content = func(content, message.author, irc_client, message.server)

       # Insert a zero-width space so people with the same name on IRC don't get pinged.
    author = prevent_ping(message.author.name)

    try:
        irc_client.send("PRIVMSG", target=get_config("mainserver.irc.irc.channel"), message="<{}> {}".format(author, content))
    except RuntimeError:
        pass

"""
@command_help("irc", "Commands for interacting with IRC.", "irc who")
@command("irc who")
async def irc_command(content, match, message):
    """


def prevent_ping(name: str):
    return name[:1] + "\u200B" + name[1:]

@irc_transform
def convert_disc_mention(message, author, irc_client, discord_server):
    try:
        return MENTION_RE.sub(lambda match: "@{}".format(prevent_ping(discord_server.get_member(match.group(1)).name)), message)
    except:
        logger.exception("shit")
        return message

@discord_transform
def convert_irc_mention(message, author, discord_server, irc_client):
    try:
        return IRC_MENTION_RE.sub(lambda match: "<@{}>".format(discord_server.get_member_named(match.group(1)).id), message)
    except:
        logger.exception("Unable to convert mention to user ID")
        return message
