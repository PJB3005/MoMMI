import logging
import asyncio
import heapq
import pytz
from datetime import datetime, timedelta
from typing import Any, Dict, Match, List, Tuple, Set, cast
from MoMMI import MChannel, comm_event, SnowflakeID, add_reaction, master 
from discord import Message, Embed

import json

LOOP_TASK_CACHE = "nudge_mirror_task"
REMINDER_QUEUE = "nudge_mirror_queue"
LOOP_INTERVAL = 5

# Tuple format: time, message, server, channel
REMINDER_TUPLE_TYPE = Tuple[datetime, str, SnowflakeID, SnowflakeID]


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


@comm_event("gamenudge")
async def gamenudge(channel: MChannel, message: Any, meta: str) -> None:
    logger.debug(json.dumps(message))
    try:
        password = message["pass"]
        content = message["content"]
        ping = message["ping"]

    except KeyError:
        return

    if password != channel.module_config("nudge.password"):
        return

    content = content.replace("@", "@\u200B") # Zero-Width space to prevent pings.
    orig_content = content

    if ping:
        cfg: Dict[str, Any] = channel.server_config("modules.gamenudge.ping", {})
        if not cfg.get(meta):
            logger.warning("Got a ping nudge but no set role ID!")
        else:
            ident = cfg[meta]
            role = channel.server.get_discordpy_role(SnowflakeID(ident))
            content += f" {role.mention}"

    mirror_cfg: Dict[str, Any] = channel.server_config(f"modules.gamenudge.{meta}.mirror", {})

    if "channel" in mirror_cfg:
        mirror_channel = channel.server.get_channel(mirror_cfg["channel"])
        mirror_delay = timedelta(minutes=mirror_cfg["delay"])
        heap: List[REMINDER_TUPLE_TYPE] = master.get_global_storage(REMINDER_QUEUE)
        time = utcnow() + mirror_delay

        reminder = (time, orig_content, channel.server.id, mirror_channel.id)
        heapq.heappush(heap, reminder)
        await master.save_global_storage(REMINDER_QUEUE)

    await channel.send(content)


async def reminder_loop() -> None:
    while True:
        #logger.info("A")
        await asyncio.sleep(LOOP_INTERVAL)
        try:
            await check_reminders()
        except:
            logger.exception("Exception in gamenudge mirror loop")


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
    server = master.get_server(reminder[2])
    channel = server.get_channel(reminder[3])
    await channel.send(reminder[1])


def utcnow() -> datetime:
    return datetime.now(pytz.utc)

