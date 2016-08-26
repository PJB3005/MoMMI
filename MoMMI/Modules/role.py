import logging
from ..client import client
from ..config import get_config
from ..commands import command

logger = logging.getLogger(__name__)

@command("ids")
async def reload(content, match, message):
    logger.info(str(get_config("mainserver.id")))
    server = client.get_server(str(get_config("mainserver.id")))
    for role in server.roles:
        await client.send_message(message.channel, "%s: %s" % (role.name, role.id))