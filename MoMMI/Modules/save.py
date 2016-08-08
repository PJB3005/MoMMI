from ..client import client
from ..config import get_config
from ..commands import command
from ..modules import modules
import logging


logger = logging.getLogger(__name__)

@command("save")
async def save_command(content, match, message):
    if int(get_config("owner.id", 97089048065097728)) != int(message.author.id):
        await client.send_message(message.channel, "You don't have permission, fuck off.")
        return

    for module in modules:
        if hasattr(module, "save"):
            await module.save()
