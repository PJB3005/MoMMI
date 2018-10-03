import asyncio
import logging
import struct
from typing import Match, Union, Any, Dict, List, cast
from urllib.parse import parse_qs
from discord import Message
from MoMMI import command, MChannel
from MoMMI.Modules.help import register_help

logger = logging.getLogger(__name__)

@command("serverstatus", r"stat(?:us|su)\s*(\S*)")
async def serverstatus_command(channel: MChannel, match: Match, message: Message) -> None:
    try:
        config: Dict[str, Any] = channel.server_config("modules.serverstatus")
    except:
        # No config for this server probably.
        await channel.send("No status configuration for this Discord server!")
        return

    servername = match.group(1) or config.get("default")

    if servername == "default":
        servername = config.get("default")

    if not servername:
        await channel.send("No target server provided.")
        return

    if servername == "list":
        await channel.send(f"Available server keys are: {', '.join(config.keys())}")
        return

    if servername not in config:
        await channel.send(f"Unknown key '{servername}`")
        return

    server_config = config[servername]
    address = server_config["address"]
    port = server_config["port"]

    await channel.server.master.client.add_reaction(message, "⌛")

    try:
        response = await asyncio.wait_for(server_topic(address, port, b"?status"), timeout=5)

    except asyncio.TimeoutError:
        await channel.send("Server timed out.")
        return

    except:
        await channel.send("Unknown error occured.")
        return

    mapname: str
    players: str

    try:
        if not isinstance(response, Dict):
            raise NotImplementedError("Non-list returns are not accepted.")

        mapname = response["map_name"][0]
        players = response["players"][0]

    except:
        await channel.send("Server sent unsupported response.")
        return

    await channel.send(f"{players} players online, map is {mapname}.")

async def server_topic(address: str, port: int, message: bytes) -> Union[float, Dict[str, List[str]]]:
    if message[0] != 63:
        message = b"?" + message

    # Send a packet to trick BYOND into doing a world.Topic() call.
    # https://github.com/N3X15/ss13-watchdog/blob/master/Watchdog.py#L582
    packet = b"\x00\x83"
    packet += struct.pack(">H", len(message) + 6)
    packet += b"\x00" * 5
    packet += message
    packet += b"\x00"

    reader, writer = await asyncio.open_connection(address, port)
    writer.write(packet)

    await writer.drain()

    if await reader.read(2) != b"\x00\x83":
        raise IOError("BYOND server returned data invalid.")

    # Read response
    size = struct.unpack(">H", await reader.read(2))[0]
    response = await reader.read(size)
    # logger.info(response)
    writer.close()

    ret = decode_packet(response)
    if isinstance(ret, str):
        return parse_qs(ret)

    return ret

# Turns the BYOND packet into either a string or a float.
def decode_packet(packet: bytes) -> Union[float, str]:
    if packet[0] == 0x2a:
        return cast(float, struct.unpack(">f", packet[1:5])[0])

    elif packet[0] == 0x06:
        return packet[1:-1].decode("ascii")

    raise NotImplementedError(f"Unknown BYOND data code: 0x{packet[0]:x}")


async def status_help(channel: MChannel, message: Message) -> None:
    out = """REEEEE IS THE SERVER DOWN?

The answer is quite simple: ~~yes.~~ just run @MoMMI status <server>.

On *this Discord server*, you can check status for the following servers: """

    config: Dict[str, Any] = channel.server_config("modules.serverstatus")
    out += ", ".join(config.keys())

    return out

async def load(loop: asyncio.AbstractEventLoop) -> None:
    register_help(__name__, "status", status_help)
