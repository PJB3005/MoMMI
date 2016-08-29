from ..client import client
from ..commands import always_command
import re
import logging

logger = logging.getLogger(__name__)

@always_command(True)
async def WHEN(message):
    match = re.search("when[*?.!)]*$", message.content, re.IGNORECASE)
    if match == None:
        return

    if message.channel.name not in ["code-map-sprite", "general"]:
        return

    await client.send_message(message.channel, "When You Code It.")