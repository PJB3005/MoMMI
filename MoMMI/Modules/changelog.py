import logging
from ..commloop import comm_event
from ..client import client
from ..config import get_config

logger = logging.getLogger(__name__)

last_changelog_name = None
# These may or may not appear broken on your end, they look fine in Discord.
changelog_emojis = {
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


@comm_event
async def changelog_event(msg):
    global last_changelog_name
    if msg["type"] != "changelog":
        return

    msg = msg["cont"]

    author = msg["author"]
    changes = msg["changes"]
    if len(changes) == 0:
        return

    message = ""
    if author != last_changelog_name:
        message += "**__%s__** Updated:\n" % (author)
        last_changelog_name = author

    for change in changes:
        change = dicttotuples(change)[0]
        message += "%s `%s`\n" % (changelog_emojis[change[0]], change[1])

    channel = client.get_channel(str(get_config("mainserver.channels.changelog")))
    await client.send_message(channel, message)


def dicttotuples(dict):
    return [(k, v) for k, v in dict.items()]
