from typing import Match
from discord import Message
from MoMMI import command, MChannel


@command("testmerge_dummy", "testmerge")
async def testmerge_dummy_command(channel: MChannel, match: Match, message: Message) -> None:
    await channel.send("Sorry dude you got the wrong MoMMI. <@211414753925398528> is still in charge of test merges.")
