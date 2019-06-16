import logging
from typing import Match, Any, Dict
import aiohttp
from discord import Message
from MoMMI import comm_event, command, MChannel, always_command

logger = logging.getLogger(__name__)

@comm_event("ss14")
async def ss14_nudge(channel: MChannel, message: Any, meta: str) -> None:
    try:
        config: Dict[str, Any] = channel.module_config(f"ss14.servers.{meta}")
    except ValueError:
        return

    expect_password = config["password"]
    if expect_password != message.get("password"):
        return

    if "type" not in message or "contents" not in message:
        return

    contents = message["contents"]
    type = message["type"]

    if type == "ooc":
        final_message = f"\u200B**OOC**: `{contents['sender']}`: {contents['contents']}"
    else:
        return

    await channel.send(final_message)

@always_command("ss14_relay", unsafe=True)
async def ss14_relay(channel: MChannel, match: Match, message: Message) -> None:
    if not channel.internal_name:
        return

    content = message.content
    content = content.strip()

    if not content or content[0] == "\u200B":
        return

    server = None

    config: Any
    for config in channel.server_config("modules.ss14", []):
        if config["discord_channel"] != channel.internal_name:
            continue

        server = config["server"]

    if not server:
        return

    config = channel.module_config(f"ss14.servers.{server}")
    password = config["password"]
    url = config["api_url"] + "/ooc"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"password": password, "sender": message.author.name, "contents": content}) as resp:
            r = await resp.text()
            logger.error(f"{resp.status}")
