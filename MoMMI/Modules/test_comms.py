from typing import Any
from MoMMI import comm_event, MChannel


@comm_event("testing")
async def derp(channel: MChannel, message: Any, meta: str) -> None:
    await channel.send(message)
