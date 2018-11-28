from ..client import client
from ..commands import always_command
import re
import logging
import random

logger = logging.getLogger(__name__)

"""
@always_command(True)
async def WHEN(message):
    match = re.search("when[*?.!)]*$", message.content, re.IGNORECASE)
    if match is None:
        return

    if random.random() > 0.001:
        await client.send_message(message.channel, "When You Code It.")
    else:
        await client.send_message(message.channel, "Never.")
"""
