from ..commands import always_command
from ..util import output
from ..config import get_config
import logging
import asyncio
import bottom


irc_client = irc_client = bottom.Client(
    host=get_config("mainserver.irc.irc.address"),
    port=get_config("mainserver.irc.irc.port"),
    loop=asyncio.get_event_loop(),
    ssl=True
)
logger = logging.getLogger(__name__)


async def unload(loop=None):
    logger.info("Dropping IRC connection.")
    await irc_client.disconnect()


@irc_client.on("client_connect")
async def connect(**kwargs):
    logger.info("Connected")
    irc_client.send("NICK", nick="PJBot_")
    irc_client.send("USER", user="PJBot", realname="https://github.com/PJB3005/MoMMI")
    irc_client.send('JOIN', channel='#mommi')

asyncio.ensure_future(irc_client.connect(), loop=irc_client.loop)
