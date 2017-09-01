from MoMMI.commands import command

@command("shutdown", "shutdown", roles=["owner"])
async def shutdown_command(channel, match, message):
    await channel.send("Shutting down!")
    await channel.server.master.shutdown()

@command("test", "shit")
async def plane(channel, match, message):
    await channel.send(random.choice(channel.module_config(__name__, "responses")))
