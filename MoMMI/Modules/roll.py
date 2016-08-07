from ..client import client
from ..commands import command
import logging
import random

logger = logging.getLogger(__name__)

@command("roll\s*(-?\d+)\s*(-?\d+)")
async def roll(content, match, message):
    random.seed()
    msg = str(random.randint(int(match.group(1)), int(match.group(2))))
    await client.send_message(message.channel, msg)

@command("(?:pick|choose)\s*\((.*?)\)")
async def pick(content, match, message):
    random.seed() 
    choices = [x.strip() for x in match.group(1).split(",")]
    if len(choices) < 2:
        await client.send_message(message.channel, "You need to provide at least 2 options.")
        return

    if len(set(choices)) != len(choices):
        await client.send_message(message.channel, "If you think you're funny by spamming duplicates, you're not. Asshole.")
        return


    chosen = random.choice(choices)

    await client.send_message(message.channel, "**%s**" % (chosen))
