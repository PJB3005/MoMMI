from typing import Match
from discord import Message
from MoMMI.commands import command
from MoMMI.channel import MChannel
from MoMMI.role import MRoleType

@command("shutdown", "shutdown", roles=[MRoleType.OWNER])
async def shutdown_command(channel: MChannel, match: Match, message: Message):
    await channel.send("Shutting down!")
    await channel.server.master.shutdown()
