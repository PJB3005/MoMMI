from MoMMI.commloop import comm_event


@comm_event("testing")
async def derp(channel, message):
    await channel.send(message)
