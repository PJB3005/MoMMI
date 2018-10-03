import asyncio
import heapq
import re
from datetime import datetime, timedelta
from logging import getLogger
from typing import Match, List, Tuple, Set, cast
import dateutil.parser
import pytz
from discord import Message, Embed
from MoMMI import MChannel, command, master, SnowflakeID, add_reaction, MRoleType
from MoMMI.Modules.help import register_help

LOOP_TASK_CACHE = "reminder_task"
REMINDER_QUEUE = "reminder_queue"
REMINDER_UID = "reminder_uid"
LOOP_INTERVAL = 5
LOGGER = getLogger(__name__)
DATE_RE = re.compile(r"^(?:(\d{4})[/-](\d\d)[/-](\d\d))?(?:(?(1)@)(\d\d)(?::(\d\d)(?::(\d\d))?)?)?$")
RELATIVE_DATE_SECTION_RE = re.compile(r"(\d+)([dhmsw])")
RELATIVE_DATE_VERIFY_RE = re.compile(r"^(?:\d+[dhmsw])+$")
# Tuple format: time, message, server, channel, member, uid
REMINDER_TUPLE_TYPE = Tuple[datetime, str, SnowflakeID, SnowflakeID, SnowflakeID, int]

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

    if not master.has_global_storage(REMINDER_UID):
        master.set_global_storage(REMINDER_UID, 0)


async def unload(loop: asyncio.AbstractEventLoop) -> None:
    if master.has_cache(LOOP_TASK_CACHE):
        task: asyncio.Future = master.get_cache(LOOP_TASK_CACHE)
        task.cancel()
        master.del_cache(LOOP_TASK_CACHE)


async def reminder_loop() -> None:
    while True:
        print("tick")
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
        # LOGGER.debug("Yes?")
        item = heap[0]
        heapq.heappop(heap)
        # heapq.heapify(heap)
        modified = True

        asyncio.ensure_future(send_reminder(item))

    if modified:
        await master.save_global_storage(REMINDER_QUEUE)


async def send_reminder(reminder: REMINDER_TUPLE_TYPE) -> None:
    server = master.get_server(reminder[2])
    channel = server.get_channel(reminder[3])
    await channel.send(f"*Buzz* <@{reminder[4]}> {reminder[1]}")


@command("remindlist", r"remindlist(?:\s+<@!?(\d+)>)?")
async def remindlist_command(channel: MChannel, match: Match, message: Message) -> None:
    snowflake = SnowflakeID(message.author.id)
    if match[1] is not None:
        if not channel.isrole(message.author, MRoleType.ADMIN):
            await channel.send("No perms lad.")
            return

        snowflake = SnowflakeID(match[1])

    serv_id = channel.server.id
    queue = filter(lambda x: x[4] == snowflake and x[2] == serv_id, master.get_global_storage(REMINDER_QUEUE))
    embed = Embed()
    desc = "All reminders for that user ID, contents hidden:\n"
    for entry in queue:
        if len(entry) > 5:  # It has a UID.
            desc += f"{entry[5]}: "

        t = entry[0].astimezone(pytz.utc)
        pretty = t.strftime("%A %d %B %Y %H:%M:%S %Z")
        desc += f"{pretty} <#{entry[3]}>\n"

    embed.description = desc
    await channel.send(embed=embed)


@command("unremind", r"unremind\s+(\d+)")
async def unremind_command(channel: MChannel, match: Match, message: Message) -> None:
    uid = int(match[1])
    serv_id = channel.server.id
    thelist = master.get_global_storage(REMINDER_QUEUE)
    for x in master.get_global_storage(REMINDER_QUEUE):
        if len(x) > 5 and x[5] == uid:
            if x[2] != serv_id:
                await channel.send("That reminder UID doesn't belong to this server, hands off.")
                return

            if x[4] != SnowflakeID(message.author.id):
                if not channel.isrole(message.author, MRoleType.ADMIN):
                    await channel.send("You're not touching that without admin perms dude.")
                    return

            found = x
            break

    thelist.remove(found)
    heapq.heapify(thelist)
    asyncio.ensure_future(master.save_global_storage(REMINDER_QUEUE))
    await channel.send("And away it goes.")


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

    uid = master.get_global_storage(REMINDER_UID)
    master.set_global_storage(REMINDER_UID, uid + 1)
    reminder = (time, match.group(2), channel.server.id, channel.id, SnowflakeID(message.author.id), uid)
    heapq.heappush(heap, reminder)
    pretty = time.strftime("%A %d %B %Y %H:%M:%S **%Z**")
    await channel.send(f"#{uid} coming in at {pretty}")
    asyncio.ensure_future(add_reaction(message, "✅"))
    asyncio.ensure_future(master.save_global_storage(REMINDER_QUEUE))
    asyncio.ensure_future(master.save_global_storage(REMINDER_UID))


@command("sneakremind", r"sneakremind\s+(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(.+)", roles=[MRoleType.OWNER])
async def sneakremind_command(channel: MChannel, match: Match, message: Message) -> None:
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

    uid = master.get_global_storage(REMINDER_UID)
    master.set_global_storage(REMINDER_UID, uid + 1)
    reminder = (time, match.group(5), SnowflakeID(match.group(2)), SnowflakeID(match.group(3)), SnowflakeID(match.group(4)), uid)
    heapq.heappush(heap, reminder)
    pretty = time.strftime("%A %d %B %Y %H:%M:%S **%Z**")
    await channel.send(f"#{uid} coming in at {pretty}")
    asyncio.ensure_future(add_reaction(message, "✅"))
    asyncio.ensure_future(master.save_global_storage(REMINDER_QUEUE))
    asyncio.ensure_future(master.save_global_storage(REMINDER_UID))


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

        keys_done: Set[str] = set()

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
        pass

    # ISO 8601
    try:
        # Mypy fails to find this method? Odd.
        time = dateutil.parser.isoparse(timestring)  # type: ignore
        if not time.tzinfo:
            time = time.replace(tzinfo=pytz.utc)

        else:
            time = time.astimezone(pytz.utc)

        return cast(datetime, time)

    except:
        pass

    raise Exception("Unknown date format.")


def utcnow() -> datetime:
    return datetime.now(pytz.utc)


register_help(__name__, "reminders", f"""For when you're forgetful like me.
You can set reminders to be reminded of *things* later.

The basic syntax is as follows:
@MoMMI remind 5m fix that got damn broken Discord bot.
where 5m is a time or date specifier, here "in 5 minutes". Anything after that is a handy message you can insult yourself with.
Time specifiers can be of 3 types:
* Relative, such as the first example. They work by smashing a number and a unit together, units being w d h m s for week day hour minute and second. You can do stuff like 1d12h.
* YYYY/MM/DD@hh:mm:ss date specifier: pretty simple as long as you're not American. Time of day can be left out.
* ISO-8601. Of course. Also the only way you're entering non-UTC time zones because screw that otherwise.

All times are handled in UTC because it's absolutely the only way I'm maintaining my sanity let's be honest: https://www.youtube.com/watch?v=-5wpm-gesOY
Seriously I'm using Python which is supposed to be *batteries included* and I had to pull in TWO libraries from PyPI just to make this module. That's enough.
Tom Scott was right.

MoMMI will confirm when the reminder is gonna be sent (within {LOOP_INTERVAL} second accuracy), as well as giving a UID with a # prefix.
You can later delete the reminder by doing @MoMMI unremind <UID>, provided you're not too late.

You can also get a list of all reminders (contents excluded) for you on a server by doing @MoMMI remindlist. This command will also print UIDs.

Admins can view reminders for others on the server by doing @MoMMI remindlist @ShitposterAboutToBeBanned. They can also delete reminders for other users. Remember with great power comes great responsability yada yada.
""")
