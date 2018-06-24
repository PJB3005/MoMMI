from typing import Match
from discord import Message
from MoMMI import MChannel, master, command

@command("dance", "dance")
async def dance(channel: MChannel, match: Match, message: Message) -> None:
    await master.client.send_file(message.channel, "/home/pj/MoMMI/Files/wiggle.gif")
