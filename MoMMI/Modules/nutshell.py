from typing import Match
from discord import Message
from MoMMI import MChannel, master, command

@command("nutshell", "nutshell")
async def dance(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send("https://cdn.discordapp.com/attachments/310780221156491265/647941568631799831/Soap.webm")