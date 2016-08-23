from ..client import client
from ..commands import always_command
import re
import logging

logger = logging.getLogger(__name__)

@always_command(True)
async def WHEN(message):
    if not re.match("when[*?.!)]*$", message.content, re.IGNORECASE):
        #logger.warning("nope")
        return

    if message.channel.name not in ["code-map-sprite", "general"]:
        #logger.warning(message.channel.name)
        return

    await client.send_message(message.channel, "When You Code It.")