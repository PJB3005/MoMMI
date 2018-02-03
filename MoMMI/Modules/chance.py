import random
from MoMMI.commands import command

@command("pick", r"(?:pick|choose)\s*\((.*?)\)")
async def pick_command(channel, match, message):
    choices = [x.strip() for x in match.group(1).split(",")]
    if len(choices) < 2:
        await channel.send("You need to provide at least 2 options.")
        return

    choice = random.choice(choices)
    await channel.send(f"**{choice}**")

@command("roll", r"(\d+)d(\d+)")
async def roll_command(channel, match, message):
    result = "Results: "
    for i in range(0, int(match.group(1))):
        if i > 0:
            result += ", "
        result += str(random.randint(1, int(match.group(2))))
    await channel.send(result)
