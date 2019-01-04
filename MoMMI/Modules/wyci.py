import random
import re
from typing import Match
from discord import Message
from MoMMI import master, always_command, MChannel

@always_command("wyci")
async def wyci(channel: MChannel, _match: Match, message: Message) -> None:
    if not channel.server_config("wyci.enabled", True):
        return
    
    match = re.search(r"\S\s+when[\s*?.!)]*$", message.content, re.IGNORECASE)
    if match is None:
        return

    if random.random() > 0.001:
        await channel.send("When You Code It.")
    else:
        await channel.send("Never.")

