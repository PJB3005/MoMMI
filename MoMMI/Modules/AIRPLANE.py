import random
import re
from discord import Message
from typing import re as typing_re, TYPE_CHECKING
from ..commands import command

if TYPE_CHECKING:
    from ..server import MChannel


@command("airplane", "\u2708", flags=re.UNICODE|re.IGNORECASE)
async def plane(channel: "MChannel", match: typing_re.Match, message: Message):
    await channel.send(random.choice(channel.module_config(__name__, "responses")))
