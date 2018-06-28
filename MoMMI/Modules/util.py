from typing import Match
from discord import Message, Embed
from MoMMI import MChannel, MRoleType, command

@command("ids", r"ids", roles=[MRoleType.OWNER])
async def ids_command(channel: MChannel, match: Match, message: Message) -> None:
    server = message.server
    desc = ""
    for role in server.roles:
        if role.name[0] == "@":
            continue
        desc += f"{role.name}: `{role.id}`\n"

    embed = Embed()
    embed.description = desc
    await channel.send(embed=embed)
