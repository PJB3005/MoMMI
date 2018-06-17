import asyncio
from typing import Match
import aiohttp
from discord import Message
from MoMMI.commands import command
from MoMMI.master import master
from MoMMI.server import MChannel
from MoMMI.role import MRoleType


@command("reload", "reload", roles=[MRoleType.OWNER])
async def reload(channel: MChannel, match: Match, message: Message):
    errors = await master.reload_modules()

    if errors:
        await master.client.add_reaction(message, "🤒")

    else:
        await master.client.add_reaction(message, "👌")


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


@command("name", r"name\s+(.+)", roles=[MRoleType.OWNER])
async def name_command(channel: MChannel, match: Match, message: Message):
    await master.client.edit_profile(username=match.group(1))


@command("nick", r"nick\s+(.+)", roles=[MRoleType.OWNER])
async def nick_command(channel: MChannel, match: Match, message: Message):
    member = message.server.get_member(master.client.user.id)
    await master.client.change_nickname(member, match.group(1))


@command("avatar", r"avatar", roles=[MRoleType.OWNER])
async def avatar_command(channel: MChannel, match: Match, message: Message):
    attachment = message.attachments[0]["url"]
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment) as request:
            data = await request.read()

    await master.client.edit_profile(avatar=data)

@command("save", r"save", roles=[MRoleType.OWNER])
async def avatar_command(channel: MChannel, match: Match, message: Message):
    for server in master.servers.values():
        await server.save_all_storages()
