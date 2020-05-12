import random
import re
from typing import Match
from discord import Message
from MoMMI import master, always_command, MChannel

@always_command("based")
async def based(channel: MChannel, _match: Match, message: Message) -> None:
    if not channel.server_config("based.enabled", True):
        return

    match = re.search(r"\S\s+(based)[\s*?.!)]*$", message.content, re.IGNORECASE)
    if match is None:
        return

    if random.random() > 0.005:
        await channel.send("Based on what?")
    else:
        await channel.send("Not Based.")
