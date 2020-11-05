from typing import Match
from discord import Message, Embed
from MoMMI import master, command, MChannel


@command("userinfo_command", r"userinfo\s*(?:<@!?)(\d+)>?")
async def userinfo(channel: MChannel, match: Match, message: Message) -> None:
    server = channel.server
    userId = match[1]
    user = await master.client.get_user_info(userId)
    
    embed = Embed()
    embed.add_field(name="Created at", value=str(user.created_at))
    
    await channel.send(embed=embed)
    
