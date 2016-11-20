import asyncio
import logging
from typing import List
from discord import Channel, ChannelType, VoiceClient, voice_client, Member, Message, Server
from discord.voice_client import StreamPlayer
from .client import client

logger = logging.getLogger(__name__)


class VoiceManager(object):
    def __init__(self, server: Server):
        self.voice = None  # type: VoiceClient
        self.player = None  # type: StreamPlayer
        self.queue = []  # type: List[str]
        self.server = server  # type: Server
        self.lock = False  # type: bool

    def queue_url(self, url: str):
        self.queue.append(url)

    def dequeue(self) -> str:
        if len(self.queue) == 0:
            return None

        return self.queue.pop(0)

    def stop_player(self):
        self.player._callback_target = None
        self.player.stop()
        self.player = None

    async def start_player(self, url: str, channel: Channel, ignore_current_player: bool=False):
        if self.player is not None and not ignore_current_player:
            logger.warning("Already had a player. Shutting it down.")
            self.stop_player()

        logger.info(self.player)

        if url is None:
            logger.info("No URL passed, getting from queue.")
            url = dequeue()
            if url is None:
                logger.error("No URL to play!")

        # Get the current channel playing.
        if channel is None:
            if self.voice is not None:
                channel = self.voice.channel

            else:
                logger.error("Attempted to start a player without channel OR current connection.")
                return

        await self.join_channel(channel)

        self.player = await self.voice.create_ytdl_player(url, after=after_callback)
        self.player._callback_target = self
        self.player.start()
        logger.info("Started playing URL %s and created the ytdl player %s", url, self.player)

    async def join_channel(self, channel: Channel):
        if channel.server != self.server:
            raise ValueError("Attempted to join a channel on a different server.")

        if self.voice is not None:
            if self.voice.channel.id == channel.id:
                logger.info("Tried to join a channel that we are already on. Ignoring.")
                return

            logger.info("Moving channel.")
            self.voice = await self.voice.move_to(channel)
            return

        self.voice = await client.join_voice_channel(channel)
        logger.info("Joined channel %s, voice client: %s", channel.name, self.voice)

    async def leave_voice(self):
        if self.lock:
            return

        if self.voice is None:
            logger.warning("Tried to leave voice, but we're not connected!")
            return

        if self.player is not None:
            logger.info("Stopping player due to voice leave!")
            self.stop_player()

        logger.info("Disconnecting...")
        await self.voice.disconnect()
        self.voice = None
        logger.info("Disconnected")

    async def next_in_queue(self):
        logger.info("Next in queue ran.")
        logger.info(self.queue)
        url = self.dequeue()  # type: str
        logger.info(url)
        self.player = None
        if url is None:
            logger.info("Nothing left in the queue. Stop!")
            await self.leave_voice()
            return

        await self.start_player(url, None, True)


def after_callback(player: StreamPlayer):
    logger.info("Callback ran, continuing queue.")

    if hasattr(player, "_callback_target") and player._callback_target is not None:
        loop = player._callback_target.voice.loop  # type: asyncio.AbstractEventLoop
        loop.create_task(player._callback_target.next_in_queue())


def get_voice_manager(server: Server) -> VoiceManager:
    manager = VOICE_MANAGERS.get(server)  # type: VoiceManager
    if manager is not None:
        return manager

    manager = VoiceManager(server)
    VOICE_MANAGERS[server] = manager
    return manager


# Dictionary of server IDs: voice manager for the server.
VOICE_MANAGERS = {}  # Dict[Server, VoiceManager]
