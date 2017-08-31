import aiohttp
import asyncio
import json
import logging
import re
import os
import subprocess
from colorhash import ColorHash
from discord import Colour, Embed, Message
from MoMMI.commloop import comm_event
from MoMMI.server import MChannel
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Taken from https://github.com/d3athrow/vgstation13/blob/Bleeding-Edge/bot/plugins/GitHub.py
REG_PATH = re.compile(r"\[([a-zA-Z\-_/][a-zA-Z0-9\- _/]*\.[a-zA-Z]+)(#L\d+(?:-L\d+)?)?\]", re.I)
REG_ISSUE = re.compile(r"\[#?([0-9]+)\]")
REG_BRACKETS = re.compile(r"\[(.+?)\]")

COLOR_GITHUB_RED = Colour(0xFF4444)
COLOR_GITHUB_GREEN = Colour(0x6CC644)
COLOR_GITHUB_PURPLE = Colour(0x6E5494)
MAX_BODY_LENGTH = 200
MD_COMMENT_RE = re.compile(r"<!--.*-->", flags=re.DOTALL)



@comm_event("github_event")
async def github_event(channel: MChannel, message, meta):
    event = message['event']
    logger.debug(f"Handling GitHub event '$YELLOW{event}$RESET' to '$YELLOW{meta}$RESET'")

    # Find a function by the name of `on_github_{event}` in globals and call it.
    func = globals().get(f"on_github_{event}")
    if func is None:
        logger.debug("No handler for this event, ignoring.")
        return

    await func(channel, message["data"], meta)


async def on_github_push(channel: MChannel, message, repo):
    embed = Embed()
    embed.set_author(name=message["sender"]["login"], url=message["sender"]["html_url"], icon_url=message["sender"]["avatar_url"])
    embed.set_footer(text=repo)
    embed.title = "New commits"

    content = ""
    for commit in message["commits"]:
        message = commit["message"]
        if len(message) > 67:
            message = message[:67] + "..."
        content += f"`{commit['id'][:7]}` {message}\n"

    embed.description = content

    await channel.send(embed=embed)

