import logging
from ..client import client
from ..config import get_config
from ..commands import command

logger = logging.getLogger(__name__)

@command("ids")
async def reload(content, match, message):
    for role in client.get_server(get_config("mainserver.id")).roles:
        await client.send_message(message.channel, "%s: %s" % (role.name, role.id))