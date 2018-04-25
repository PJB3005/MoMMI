from MoMMI.commands import command
from MoMMI.master import master

@command("dance", "dance")
async def dance(channel, match, message):
    await master.client.send_file(message.channel, "/home/pj/MoMMI/Files/wiggle.gif")
