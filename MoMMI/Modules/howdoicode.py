from typing import Match
from discord import Message
from MoMMI import MChannel, master, command

@command("howdoicode", "howdoicode")
async def dance(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send("https://docs.spacestation14.io/en/getting-started/how-do-i-code")
