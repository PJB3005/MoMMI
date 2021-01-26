import logging
import random
import re
import functools
from collections import defaultdict
from typing import DefaultDict, Match, Iterable, Dict
from discord import Message, Member
from MoMMI.commands import command, always_command
from MoMMI.server import MChannel
from MoMMI import SnowflakeID, add_reaction

logger = logging.getLogger(__name__)

@always_command("resp_read")
async def resp_read(channel: MChannel, match: Match, message: Message) -> None:
    if not message.content.startswith("$"):
        return
    
    try:
        data: Dict[str, str] = channel.get_storage("resp")
    except KeyError:
        return


    resp = data.get(message.content[1:])

    if resp:
        await channel.send(resp)

@command("resp_remove", r"resp\s+remove\s+(\S+)")
async def resp_remove(channel: MChannel, match: Match, message: Message) -> None:
    if not await can_modify(channel, message.author):
        return
    
    name = match.group(1)

    try:
        data: Dict[str, str] = channel.get_storage("resp")
    except KeyError:
        await add_reaction(message, "❓")
        return

    del data[name]

    await channel.save_storage("resp")
    await add_reaction(message, "✅")


@command("resp_add", r"resp\s+add\s+(\S+)\s+(.+)")
async def resp_add(channel: MChannel, match: Match, message: Message) -> None:
    if not await can_modify(channel, message.author):
        return
    
    name = match.group(1)
    value = match.group(2)

    try:
        data: Dict[str, str] = channel.get_storage("resp")
    except KeyError:
        data = {}
        channel.set_storage("resp", data)

    data[name] = value

    await channel.save_storage("resp")
    await add_reaction(message, "✅")

@command("resp_list", r"resp\s+list")
async def resp_list(channel: MChannel, match: Match, message: Message) -> None:
    try:
        data: Dict[str, str] = channel.get_storage("resp")
    except KeyError:
        data = {}

    s = ", ".join(data.keys())

    await channel.send(f"Your options are: {s}\nChoose wisely.")


async def can_modify(channel: MChannel, user: Member) -> bool:
    role = channel.server_config("modules.responses.role")

    for r in user.roles:
        if r.id == role:
            return True

    await channel.send("You are not allowed to do that")
    return False
