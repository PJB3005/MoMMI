from typing import Match
from discord import Message
from MoMMI import MRoleType, MChannel, command

@command("testperm", "testperm\s+(\S+)")
async def testperm_command(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send(str(channel.isrole(message.author, MRoleType[match[1]])))
