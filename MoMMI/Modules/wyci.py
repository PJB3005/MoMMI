from MoMMI import master, always_command
import re
import random

@always_command("wyci")
async def wyci(channel, match, message) -> None:
    match = re.search("\S\s+when[\s*?.!)]*$", message.content, re.IGNORECASE)
    if match is None:
        return

    if random.random() > 0.001:
        await channel.send("When You Code It.")
    else:
        await channek.send("Never.")

