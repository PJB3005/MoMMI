import logging
import struct
import asyncio
from urllib.parse import parse_qs
from ..client import client
from ..commands import command, command_help
from ..config import get_config


logger = logging.getLogger(__name__)

@command_help("status", "Output the status of the game server.", "status [server]", "The server defaults to the main server if not specified.")
@command("status\s*(\S*)")
async def status_command(content, match, message):
    server = match.group(1) or get_config("gameservers.default")

    address = get_config("gameservers.%s.address" % (server))
    port = get_config("gameservers.%s.port" % (server))

    try:
        response = await asyncio.wait_for(server_topic(address, port, b"?status"), timeout=5)

    except:
        await client.send_message(message.channel, "Unable to connect to server")
        return

    map = response["map_name"][0]
    playing = response["players"][0]

    content = "**%s** players, map is **%s**" % (playing, map)

    logger.info(message.channel.id)
    logger.info(get_config("mainserver.channels.admin"))

    if message.channel.id == str(get_config("mainserver.channels.admin")):
        content += ", **{0}** admins online. *Note: unable to provide AFK statistics for administrators.*".format(response["admins"][0])

    await client.send_message(message.channel, content)

async def server_topic(address, port, message):
    if message[0] != 63:
        message = b"?" + message

    # Send a packet to trick BYOND into doing a world.Topic() call.
    # https://github.com/N3X15/ss13-watchdog/blob/master/Watchdog.py#L582
    packet = b"\x00\x83"
    packet += struct.pack(">H", len(message) + 6)
    packet += b"\x00" * 5
    packet += message
    packet += b"\x00"

    logger.info(packet)

    reader, writer = await asyncio.open_connection(address, port)
    logger.info("Writing packet.")
    writer.write(packet)

    logger.info("Reading response.")
    # So FOR SOME FUCKING REASON BYOND doesn't actually SEND A FUCKING EOF.
    # ARE YOU KIDDING ME?
    # HOW DO YOU FUCK UP SOMETHING AS SIMPLE AS THIS.
    # CHRIST.
    response = b''
    while True:
        buf = await reader.read(1024)
        response += buf
        szbuf = len(buf)
        if szbuf < 1024:
            break

    writer.close()

    return parse_qs(decode_packet(response))

# Turns the BYOND packet into either a string or a float.
def decode_packet(packet):
    if packet[0:2] != b"\x00\x83":
        logger.error("Packet encoding is invalid.")
        return

    size = struct.unpack(">H", packet[2:4])[0]
    if packet[4] == 0x2a:
        return struct.unpack(">f", packet[5:9])[0]

    elif packet[4] == 0x06:
        return packet[5:-1].decode("ascii")
