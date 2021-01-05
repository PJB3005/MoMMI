from typing import Match
from discord import Message
from MoMMI import MChannel, command, master

@command("hackmd", r"hackmd(?:\s+(\S+))?")
async def hackmd(channel: MChannel, match: Match, message: Message) -> None:
    if match[1] is None:
        msg = """The official SS14 wiki https://hackmd.io/@ss14/docs/wiki"""
		await channel.send(msg)
		return 
	else:
		await channel.send("https://hackmd.io/@ss14/docs/"message)
		return
		