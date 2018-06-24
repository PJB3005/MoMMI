import asyncio
import logging
from typing import Any, TypeVar, List, Dict, Tuple
from MoMMI import comm_event, master, MChannel

LOGGER: logging.Logger = logging.getLogger(__name__)

CHANGELOG_EMOJIS = {
    "bugfix": "🐞",
    "wip": "🔜",
    "tweak": "🛠",
    "soundadd": "🎧",
    "sounddel": "🔇",
    "rscdel": "❌",
    "rscadd": "🆕",
    "imageadd": "🎨",
    "imagedel": "⬜",
    "spellcheck": "🔡",
    "experiment": "💯",
    "tgs": "💩"
}

CACHE_CHANGELOG_NAMES = "changelog_names"

async def load(loop: asyncio.AbstractEventLoop) -> None:
    if not master.has_cache(CACHE_CHANGELOG_NAMES):
        master.set_cache(CACHE_CHANGELOG_NAMES, {})


@comm_event("changelog")
async def changelog_comm_event(channel: MChannel, message: Any, meta: str) -> None:
    author = message["author"]
    changes = message["changes"]
    if not changes:
        return

    print_name = True
    cache = master.get_cache(CACHE_CHANGELOG_NAMES)
    if channel.id in cache and cache[channel.id] == author:
        print_name = False

    else:
        cache[channel.id] = author

    content = ""
    if print_name:
        content += f"**__{author}__** Updated:\n"

    for change in changes:
        change = dicttotuples(change)[0]
        emoji = CHANGELOG_EMOJIS.get(change[0], "🆕")
        content += f"{emoji} {change[1]}\n"

    await channel.send(content)


TKey = TypeVar("TKey")
TValue = TypeVar("TValue")

def dicttotuples(d: Dict[TKey, TValue]) -> List[Tuple[TKey, TValue]]:
    return [(k, v) for k, v in d.items()]

