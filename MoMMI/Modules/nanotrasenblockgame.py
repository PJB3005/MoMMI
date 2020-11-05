import re
from typing import Match
from discord import Message
from MoMMI import master, always_command, MChannel

@always_command("nanotrasenblockgame")
async def ntbg(channel: MChannel, _match: Match, message: Message) -> None:
    if not channel.server_config("modules.nanotrasenblockgame.enabled", False):
        return

    match = re.search(r".*tetris.*", message.content, re.IGNORECASE)
    if match is None:
        return

    await channel.send("*Nanotrasen Block Game:tm:")

