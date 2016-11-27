from ..client import client
from ..commands import always_command
import re
import aiofiles

@always_command(True)
async def worksonmymachine(message):
    match = re.search(r"w(e|o)rks\s*((for|4) me|((at|on|in|with)\s*m(y|ine)\s*.*))", message.content, re.IGNORECASE)
    if match is None:
        return

    await client.send_file(message.channel, "/home/pj/MoMMI/Files/worksonmymachine.png")
