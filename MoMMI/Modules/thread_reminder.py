import logging
from MoMMI import MChannel
import time


logger = logging.getLogger(__name__)

async def thread_reminder(channel: MChannel) -> None:

    # Send the message
    await channel.send("**A round has ended.** You can discuss it at https://boards.4chan.org/vg/catalog#s=ss13g. This channel will be closed for 10 minutes.")
    # And make it closed
    await channel.close()
    # For 10 minutes
    time.sleep(600)
    # And open it
    await channel.send("**This channel is open for discussion again.**")
    await channel.open()
