from MoMMI.commands import command


@command("testmerge_dummy", "testmerge")
async def testmerge_dummy_command(channel, match, message):
    await channel.send("Sorry dude you got the wrong MoMMI. <@211414753925398528> is still in charge of test merges.")
