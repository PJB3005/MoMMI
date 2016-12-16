import logging
import re
from ..client import client
from ..commloop import comm_event
from ..config import get_config
from ..util import getrole

logger = logging.getLogger(__name__)


@comm_event
async def gamenudge(msg):
    if msg["type"] != "nudge":
        return

    logger.info("Receiving a game message!")
    msg = msg["cont"]

    if msg["pass"] != get_config("nudges.password"):
        logger.warning("Invalid password!")
        return

    channelid = 0
    if msg.get("admin", False):
        channelid = get_config("mainserver.channels.admin")
    else:
        channelid = get_config("mainserver.channels.main")

    channel = client.get_channel(str(channelid))
    if not channel:
        logger.error("Unable to get a reference to the channel! Is the ID incorrect?")
        return

    output = msg["content"].replace("@", "@​")
    if msg["ping"]:
        output += " " + getrole(channel.server, str(get_config("mainserver.roles.admin"))).mention

    logger.info(output)

    await client.send_message(channel, output)
