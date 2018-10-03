import asyncio
import random
from typing import Match
from discord import Message
from MoMMI import command, MChannel


@command("pick", r"(?:pick|choose)\s*\((.*?)\)")
async def pick_command(channel: MChannel, match: Match, message: Message) -> None:
    choices = [x.strip() for x in match.group(1).split(",")]
    if len(choices) < 2:
        await channel.send("You gotta provide at least 2 options.")
        return

    choice = random.choice(choices)
    await channel.send(f"**{choice}**")


@command("roll", r"(\d+)d(\d+)(?:\+(\d+))?")
async def roll_command(channel: MChannel, match: Match, message: Message) -> None:
    result = "Results: "
    count = int(match.group(1))
    if count > 100:
        await channel.send("Ok look dude. A minute or two after this dice command got implemented bobda ran a god damn 10000000000000000000000000000d10. Now because it has to ITERATE those dice and 10000000000000000000000000000 is a giant fucking number, that locked up MoMMI completely because no amount of asyncio is gonna save this madness. Thank god for SIGKILL. THEN I got pinged by Intigracy telling me MoMMI locked up. *sigh*")
        return
    total = 0
    for i in range(0, count):
        if i > 0:
            result += ", "
        roll = random.randint(1, int(match.group(2)))
        total += roll
        result += str(roll)
    mod = match.group(3)
    if mod is not None:
        result += f" + {mod}"
        total += int(mod)
    result += f" = {total}"
    await channel.send(result)


@command("rand", r"rand\s*(-?\d+)\s*(-?\d+)")
async def rand_command(channel: MChannel, match: Match, message: Message) -> None:
    msg = str(random.randint(int(match.group(1)), int(match.group(2))))
    await channel.send(msg)


@command("magic8ball", r"(?:magic|magic8ball)")
async def magic8ball_command(channel: MChannel, match: Match, message: Message) -> None:
    choice = random.choice([
        "It is certain",
        "It is decidedly so",
        "Without a doubt",
        "Yes, definitely",
        "You may rely on it",
        "As I see it, yes",
        "Most likely",
        "Outlook: Positive",
        "Yes",
        "Signs point to: Yes",
        "Reply hazy, try again",
        "Ask again later",
        "Better to not tell you right now",
        "Cannot predict now",
        "Concentrate, then ask again",
        "Do not count on it",
        "My reply is: no",
        "My sources say: no",
        "Outlook: Negative",
        "Very doubtful"
    ])
    await channel.send(choice)


async def load(loop: asyncio.AbstractEventLoop) -> None:
    from MoMMI.Modules.help import register_help

    register_help(__name__, "dice", """The party enters the AI upload.
The room's power systems are completely off. At the back of the room is a hole into the core, molten out of the reinforced wall.

*I walk up to the room's APC and see if the APC still works.*

Everybody roll a dexterity saving throw.

*@MoMMI 1d20+0*

*Results: 1 = 1*""")

    register_help(__name__, "magic8ball", """Unable to make important project decisions responsibly?
Need some reliable help from our lord and saviour RNGesus?

Simple, just run @MoMMI magic 'Do I delete the Discord server?' and let NT's latest proven MoMMI Random Number Generator Technology™ decide for you.

*Nanotrasen is not liable for any damages caused - material, bodily or psychologically - as a result of poor decision making as a result of the responses from this feature.*""")

    register_help(__name__, "pick", """Man can you believe this? People actually want to do *fair* 50/50 picks between things? Kids these days.

Fine, just run @MoMMI pick(a,b,c) with as many comma separated values as you need. Normies.""")
