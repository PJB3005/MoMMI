from ..client import client
from ..commands import command, command_help
import logging
import random

logger = logging.getLogger(__name__)

@command_help("roll", "roll a random number between 2 arguments.", "roll <number 1> <number2>")
@command("roll\s*(-?\d+)\s*(-?\d+)")
async def roll(content, match, message):
    random.seed()
    msg = str(random.randint(int(match.group(1)), int(match.group(2))))
    await client.send_message(message.channel, msg)

@command_help("pick", "Picks a random item from a provided list of choices.", "pick(<choice>, <choice>[, choice...])")
@command("(?:pick|choose)\s*\((.*?)\)")
async def pick(content, match, message):
    random.seed() 
    choices = [x.strip() for x in match.group(1).split(",")]
    if len(choices) < 2:
        await client.send_message(message.channel, "You need to provide at least 2 options.")
        return

    if len(set(choices)) != len(choices):
        await client.send_message(message.channel, "If you think you're funny by spamming duplicates, you're not.")
        return


    chosen = random.choice(choices)

    await client.send_message(message.channel, "**%s**" % (chosen))
