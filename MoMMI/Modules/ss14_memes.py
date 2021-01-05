from typing import Match
from discord import Message
from MoMMI import MChannel, master, command

@command("nutshell", "nutshell")
async def dance(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send("https://cdn.discordapp.com/attachments/310780221156491265/647941568631799831/Soap.webm")

@command("cross", "cross")
async def dance(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send("https://cdn.discordapp.com/attachments/310780221156491265/721467550390812672/unknown.png")

@command("best", "best")
async def dance(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send("https://cdn.discordapp.com/attachments/371798264405819403/795940051044401212/unknown.png")

@command("shed", "shed")
async def dance(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send("https://cdn.discordapp.com/attachments/770682801607278632/785287813331550208/poorpaul.png")

@command("welcome", "welcome")
async def dance(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send("https://cdn.discordapp.com/attachments/592999743228215299/787748888365760532/ss14crew.png")