import logging
import asyncio
import aiohttp
import heapq
import pytz
from datetime import datetime, timedelta
from typing import Any, Dict, Match, List, Tuple, Set, cast
from MoMMI import MChannel, comm_event, SnowflakeID, add_reaction, master, always_command, command, delete_command, reaction_command
from MoMMI.util import utcnow
from discord import Message, Embed, Reaction, User

import json

LOOP_TASK_CACHE = "mirror_task"
REMINDER_QUEUE = "mirror_queue"
LOOP_INTERVAL = 5

# Tuple format: time, message, sender, avatar, target_webhook, orig ID
REMINDER_TUPLE_TYPE = Tuple[datetime, str, str, str, str, SnowflakeID]

logger = logging.getLogger(__name__)

# Haha delayed mirroring literally copy pasted from reminders.
# Deal with it.

async def load(loop: asyncio.AbstractEventLoop) -> None:
    task: asyncio.Future
    if master.has_cache(LOOP_TASK_CACHE):
        logger.warning("Loop task still exists!")
        task = master.get_cache(LOOP_TASK_CACHE)
        task.cancel()

    task = asyncio.ensure_future(reminder_loop())
    master.set_cache(LOOP_TASK_CACHE, task)
    if not master.has_global_storage(REMINDER_QUEUE):
        master.set_global_storage(REMINDER_QUEUE, [])


async def reminder_loop() -> None:
    while True:
        #logger.info("A")
        await asyncio.sleep(LOOP_INTERVAL)
        try:
            await check_reminders()
        except:
            logger.exception("Exception in mirror loop")


async def check_reminders() -> None:
    heap: List[REMINDER_TUPLE_TYPE] = master.get_global_storage(REMINDER_QUEUE)
    now = utcnow()

    #logger.info(repr(heap))

    modified = False
    while heap and heap[0][0] < now:
        # logger.debug("Yes?")
        item = heap[0]
        heapq.heappop(heap)
        # heapq.heapify(heap)
        modified = True

        asyncio.ensure_future(send_reminder(item))

    if modified:
        await master.save_global_storage(REMINDER_QUEUE)


async def send_reminder(reminder: REMINDER_TUPLE_TYPE) -> None:
    msg = reminder[1]
    sender = reminder[2]
    avatar = reminder[3]
    target = reminder[4]
    
    async with aiohttp.ClientSession() as session:
        await session.post(target, json={
            "content": msg,
            "username": sender,
            "avatar_url": avatar,
            "allowed_mentions": {
                "parse": []
            }})


@delete_command("mirror_hide_delete")
async def mirrorhide_command(channel: MChannel, message: Message) -> None:
    await hidemessage(channel, message)


@reaction_command("mirror_hide_reaction")
async def mirrorhide_reaction_command(channel: MChannel, reaction: Reaction, member: User) -> None:
    if reaction.emoji != '🔇':
        return
    
    if await hidemessage(channel, reaction.message):
        await add_reaction(reaction.message, "✅")


@always_command("mirrormirroronthewall", unsafe=True)
async def mirrormirroronthewall(channel: MChannel, match: Match, message: Message) -> None:
    content = message.content
    for attachment in message.attachments:
        content += " " + attachment["url"]

    found = None
    for mirror_entry in channel.server_config("modules.mirror", []):
        if channel.server.get_channel(mirror_entry["from"]) == channel:
            found = mirror_entry
            break
    else:
        return

    target = found["to"]
    mirror_delay = timedelta(minutes=found["delay"])
    heap: List[REMINDER_TUPLE_TYPE] = master.get_global_storage(REMINDER_QUEUE)
    time = utcnow() + mirror_delay

    reminder = (time, content, message.author.name, message.author.avatar_url, target, SnowflakeID(int(message.id)))
    heapq.heappush(heap, reminder)
    await master.save_global_storage(REMINDER_QUEUE)


async def hidemessage(channel: MChannel, msg: Message) -> bool:
    # Don't scrub through the list if this channel isn't a mirrored channel.
    for mirror_entry in channel.server_config("modules.mirror", []):
        if channel.server.get_channel(mirror_entry["from"]) == channel:
            break
    else:
        return False

    thelist = master.get_global_storage(REMINDER_QUEUE)
    for x in thelist:
        if str(x[5]) == msg.id:
            found = x
            break

    else:
        return False

    thelist.remove(found)
    heapq.heapify(thelist)
    asyncio.ensure_future(master.save_global_storage(REMINDER_QUEUE))

    return True