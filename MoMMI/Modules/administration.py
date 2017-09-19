import asyncio
from typing import Match
from discord import Message
from MoMMI.commands import command
from MoMMI.master import master
from MoMMI.server import MChannel
from MoMMI.role import MRoleType

@command("reload", "reload", roles=[MRoleType.OWNER])
async def reload(channel: MChannel, match: Match, message: Message):
    await master.reload_modules()

@command("modules", "modules", roles=[MRoleType.OWNER])
async def modules(channel: MChannel, match: Match, message: Message):
    msg = "```"
    for module in channel.server.master.modules.values():
        msg += f"{module.name}:\n"
        for handler in module.handlers.values():
            msg += f"* {handler.name} ({type(handler)})\n"

    msg += "```"

    await channel.send(msg)

@command("shutdown", "shutdown", roles=[MRoleType.OWNER])
async def shutdown_command(channel: MChannel, match: Match, message: Message):
    await channel.send("Shutting down!")
    # Ensure future instead of awaiting to prevent code calling us exploding.
    asyncio.ensure_future(channel.server.master.shutdown())
