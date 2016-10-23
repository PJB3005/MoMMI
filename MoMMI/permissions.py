import logging
import asyncio
from enum import Enum
from .util import pickle_dump, pickle_load
from .config import get_config
from collections import defaultdict


class bantypes(Enum):
    commands = 1
    markov = 2


def empty_list():
    return []

logger = logging.getLogger(__name__)
logger.info("Loading ban database.")
try:
    loop = asyncio.get_event_loop()
    bans = loop.run_until_complete(pickle_load("bandb"))
except:
    logger.exception("Failed to load bandb, creating new database.")
    bans = defaultdict(empty_list)


def isowner(user):
    return user.id == str(get_config("owner.id", "nope"))


def isrole(member, id):
    if isowner(member):
        return True

    for role in member.roles:
        if str(id) == role.id:
            return True

    return False


def isbanned(user, group=bantypes.commands):
    if isowner(user):
        return False

    return int(user.id) in bans[group]

async def ban(user, group=bantypes.commands):
    if isbanned(user, group):
        return

    bans[group].append(int(user.id))

    await pickle_dump(bans, "bandb")

async def unban(user, group=bantypes.commands):
    if not isbanned(user, group):
        return

    bans[group].remove(int(user.id))

    await pickle_dump(bans, "bandb")
