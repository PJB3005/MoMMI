import asyncio
import heapq
import re
from datetime import datetime, timedelta
from logging import getLogger
from typing import Match, List, Tuple
import dateutil.parser
import pytz
from discord import Message
from MoMMI.channel import MChannel
from MoMMI.commands import command
from MoMMI.master import master
from MoMMI.types import SnowflakeID
from MoMMI.util import add_reaction

LOOP_TASK_CACHE = "reminder_task"
REMINDER_QUEUE = "reminder_queue"
LOOP_INTERVAL = 5
LOGGER = getLogger(__name__)
DATE_RE = re.compile(r"^(?:(\d{4})[/-](\d\d)[/-](\d\d))?(?:(?(1)@)(\d\d)(?::(\d\d)(?::(\d\d))?)?)?$")
RELATIVE_DATE_SECTION_RE = re.compile(r"(\d+)([dhmsw])")
RELATIVE_DATE_VERIFY_RE = re.compile(r"^(?:\d+[dhmsw])+$")
# Tuple format: time, message, server, channel, member, uid
REMINDER_TUPLE_TYPE = Tuple[datetime, str, SnowflakeID, SnowflakeID, SnowflakeID]

async def load(loop: asyncio.AbstractEventLoop) -> None:
    task: asyncio.Future
    if master.has_cache(LOOP_TASK_CACHE):
        LOGGER.warning("Loop task still exists!")
        task = master.get_cache(LOOP_TASK_CACHE)
        task.cancel()

    task = asyncio.ensure_future(reminder_loop())
    master.set_cache(LOOP_TASK_CACHE, task)
    if not master.has_global_storage(REMINDER_QUEUE):
        master.set_global_storage(REMINDER_QUEUE, [])


async def unload(loop: asyncio.AbstractEventLoop) -> None:
    if master.has_cache(LOOP_TASK_CACHE):
        task: asyncio.Future = master.get_cache(LOOP_TASK_CACHE)
        task.cancel()
        master.del_cache(LOOP_TASK_CACHE)


async def reminder_loop() -> None:
    while True:
        await asyncio.sleep(LOOP_INTERVAL)
        try:
            await check_reminders()
        except:
            LOGGER.exception("Exception in reminder loop")


async def check_reminders() -> None:
    heap: List[REMINDER_TUPLE_TYPE] = master.get_global_storage(REMINDER_QUEUE)
    now = utcnow()

    modified = False
    while heap and heap[0][0] < now:
        #LOGGER.debug("Yes?")
        item = heap[0]
        heapq.heappop(heap)
        modified = True

        asyncio.ensure_future(send_reminder(item))

    if modified:
        await master.save_global_storage(REMINDER_QUEUE)


async def send_reminder(reminder: REMINDER_TUPLE_TYPE) -> None:
    server = master.get_server(reminder[2])
    channel = server.get_channel(reminder[3])
    await channel.send(f"*Buzz* <@{reminder[4]}> {reminder[1]}")


@command("reminder", r"remind(?:me|er)?\s+(\S+)\s+(.+)")
async def remind_command(channel: MChannel, match: Match, message: Message) -> None:
    heap: List[REMINDER_TUPLE_TYPE] = master.get_global_storage(REMINDER_QUEUE)
    try:
        time = parse_time(match.group(1))
    except:
        await channel.send("Invalid time format lad.")
        asyncio.ensure_future(add_reaction(message, "❌"))
        return

    if time < utcnow():
        LOGGER.debug(f"Time travel prevented, attempted was {time}")
        await channel.send("*Buzz* no time travel, nerd.")
        asyncio.ensure_future(add_reaction(message, "❌"))
        return

    reminder = (time, match.group(2), channel.server.id, channel.id, SnowflakeID(message.author.id))
    heapq.heappush(heap, reminder)
    pretty = time.strftime("%A %d %B %Y %H:%M:%S **%Z**")
    await channel.send(f"Coming in at {pretty}")
    asyncio.ensure_future(add_reaction(message, "✅"))
    asyncio.ensure_future(master.save_global_storage(REMINDER_QUEUE))


def parse_time(timestring: str) -> datetime:
    # Dates in the form YYYY/MM/DD@HH:MM:SS
    try:
        match = DATE_RE.match(timestring)
        if match is None:
            raise Exception()

        date = utcnow()

        if match.group(1) is not None:
            y = int(match.group(1))
            m = int(match.group(2))
            d = int(match.group(3))

            date = date.replace(year=y, month=m, day=d)

        if match.group(4) is not None:
            date = date.replace(hour=int(match.group(4)))

            if match.group(5) is not None:
                date = date.replace(minute=int(match.group(5)))

                if match.group(6) is not None:
                    date = date.replace(second=int(match.group(6)))

        return date

    except:
        pass

    try:
        delta = timedelta()
        if RELATIVE_DATE_VERIFY_RE.match(timestring) is None:
            raise Exception()

        keys_done = set()

        for amount, key in RELATIVE_DATE_SECTION_RE.findall(timestring):
            newa = int(amount)
            if key in keys_done:
                raise Exception()

            keys_done.add(key)

            if key == "d":
                delta += timedelta(days=newa)

            elif key == "h":
                delta += timedelta(hours=newa)

            elif key == "m":
                delta += timedelta(minutes=newa)

            elif key == "s":
                delta += timedelta(seconds=newa)

        return utcnow() + delta

    except:
        LOGGER.exception("derp")
        pass


    # ISO 8601
    try:
        time = dateutil.parser.isoparse(timestring)
        if not time.tzinfo:
            time = time.replace(tzinfo=pytz.utc)

        return time

    except:
        pass

    raise Exception("Unknown date format.")


def utcnow() -> datetime:
    return datetime.now(pytz.utc)
