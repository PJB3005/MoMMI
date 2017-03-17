from MoMMI.commloop import comm_event


@comm_event("testing")
async def derp(channel, message, meta):
    await channel.send(message)
