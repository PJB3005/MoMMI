from ..client import client
from ..commands import command
import random

choices = ["*buzz*", "*Flaps his utility arms angrily!*"]
@command("law*\s2")
async def law_2(content, match, message):
    choice = random.choice(choices)

    await client.send_message(message.channel, choice)