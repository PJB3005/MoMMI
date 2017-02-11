from ..commands import command

@command("shutdown", "shutdown", roles=["owner"])
async def shutdown(channel, match, message):
    await channel.server.master.shutdown()
