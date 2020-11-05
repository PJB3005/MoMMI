import asyncio
import logging
import struct
import aiohttp
import base64
from typing import Match, Union, Any, Dict, List, cast, Optional
from urllib.parse import parse_qs
from discord import Message
from MoMMI import command, MChannel
from MoMMI.Modules.help import register_help
from MoMMI.types import MIdentifier

logger = logging.getLogger(__name__)

@command("restart", r"restart\s*(\S*)")
async def serverstatus_command(channel: MChannel, match: Match, message: Message) -> None:
    try:
        config: Dict[str, Any] = channel.server_config("modules.restart.srv")
    except:
        # No config for this server probably.
        await channel.send("No status configuration for this Discord server!")
        return

    role: str = channel.server_config("modules.restart.role")
    servername = match.group(1)

    for r in message.author.roles:
        if r.id == role:
            break

    else:
        await channel.send("You are not allowed to do that")
        return

    if not servername:
        await channel.send("Available servers are: " + " ".join(config.keys()))
        return

    if servername not in config:
        await channel.send(f"Unknown key '{servername}`")
        return


    server_config = config[servername]
    await channel.server.master.client.add_reaction(message, "⌛")

    try:
        baseUrl = server_config["url"]
        key = server_config["key"]
        token = server_config["token"]
        
        url = baseUrl + f"/instances/{key}/restart"
        authHeader = "Basic " + base64.b64encode(f"{key}:{token}".encode("ASCII")).decode("ASCII")
        
        async with aiohttp.ClientSession() as session:
            async def load() -> Any:
                async with session.post(url, headers={"Authorization": authHeader}) as resp:
                    if resp.status != 200:
                        raise Exception(f"wrong status code: {resp.status}")

            await asyncio.wait_for(load(), timeout=5)
            
    except asyncio.TimeoutError:
        await channel.send("Server timed out.")
        return

    except:
        logger.exception("shit")
        await channel.send("Unknown error occured.")
        return
    
    await channel.send("Server restarted")
