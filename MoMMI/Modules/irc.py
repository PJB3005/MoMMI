from ..commands import unsafe_always_command, command, command_help
from ..util import output
from ..config import get_config
from ..client import client
from ..permissions import isbanned, bantypes
import logging
import asyncio
import bottom
import re


irc_client = irc_client = bottom.Client(
    host=get_config("mainserver.irc.irc.address"),
    port=get_config("mainserver.irc.irc.port"),
    loop=asyncio.get_event_loop(),
    ssl=True
)
logger = logging.getLogger(__name__)
messagelogger = logging.getLogger("IRC")
MENTION_RE = re.compile(r"<@!?(\d+)>")
IGNORED_NAMED = {"travis-ci", "vg-bot", "py-ctcp"}


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
    if nick in IGNORED_NAMED:
        return

    messagelogger.info(message)
    channel = client.get_channel(str(get_config("mainserver.irc.discord.channel")))
    await output(channel, "\u200B**IRC:** `<{}> {}`".format(nick, message))


@irc_client.on('PING')
def keepalive(message, **kwargs):
    irc_client.send('PONG', message=message)


@unsafe_always_command()
async def ircrelay(message):
    if isbanned(message.author, bantypes.irc):
        return

    if message.content[0] == "\u200B" or message.channel.id != str(get_config("mainserver.irc.discord.channel")):
        return

    content = message.content
    try:
        content = MENTION_RE.sub(lambda match: "@{}".format(prevent_ping(message.server.get_member(match.group(1)).name)), content)
    except:
        logger.exception("shit")

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
