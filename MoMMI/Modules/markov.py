import logging
import random
import re
import functools
from collections import defaultdict
from typing import DefaultDict, Match, Iterable
from discord import Message
from MoMMI.commands import command, always_command
from MoMMI.server import MChannel
from MoMMI import SnowflakeID

SENTENCE_RE = re.compile(r"([.,?\n]|(?<!@)!)")
PARENT_RE = re.compile(r"[[\]{}()\"']")
CHAIN_TYPE = DefaultDict[str, DefaultDict[str, int]]
MENTION_RE = re.compile(r"<@!?(\d+)>")
ROLE_RE = re.compile(r"<@&(\d+)>")

logger = logging.getLogger(__name__)
partial = functools.partial(defaultdict, int)

@always_command("markov_read")
async def markov_reader(channel: MChannel, match: Match, message: Message) -> None:
    # if not isbanned(message.author, bantypes.markov):

    content = PARENT_RE.sub("", message.content.lower())
    # Because chain is a referenced object.
    # We do not need to reset it explicitly.
    chain: CHAIN_TYPE
    try:
        chain = channel.get_storage("markov")
    except KeyError:
        chain = defaultdict(partial) # type: ignore
        channel.set_storage("markov", chain)

    for sentence in sentences(content):
        words = sentence.split()
        if len(words) < 7:
            continue

        last = ""

        for word in words:
            word = word.strip()
            wordchain = chain[last]
            wordchain[word] += 1
            last = word

        chain[last][""] += 1


@command("markov", r"markov\s*(?:\(?(\S*)\)?)?")
async def markov(channel: MChannel, match: Match, message: Message) -> None:
    try:
        chain = channel.get_storage("markov")
    except:
        return

    message = None
    original_seed = (match.group(1) or "").lower()
    if original_seed.endswith(")"):
        original_seed = original_seed[:-1]
    if original_seed not in chain:
        await channel.send("Cannot make markov chain: unknown word.")
        return

    # Repeat to try to prevent short chains.
    for _ in range(5):
        seed = original_seed
        message = [seed]

        # Prevent infinite loop.
        for _ in range(100):
            # Basic pickweight based on https://stackoverflow.com/questions/3679694/a-weighted-version-of-random-choice
            wordchain = chain[seed]
            # logger.info(chain)
            total = sum(wordchain.values())
            picked = random.randint(0, total)

            for word in wordchain.keys():
                picked -= wordchain[word]
                if picked <= 0:
                    seed = word
                    break

            message.append(seed)

            if seed == "":
                break

        # Remove trailing "".
        message.pop()

        if len(message) > 5:
            break

    finalmsg = " ".join(message) + "."

    # Cut out pings.
    def role_replace(match: Match) -> str:
        snowflake = SnowflakeID(match.group(1))
        role = channel.get_role_snowflake(snowflake)
        return f"@{role.name}"

    finalmsg = ROLE_RE.sub(role_replace, finalmsg)

    def user_replace(match: Match) -> str:
        snowflake = SnowflakeID(match.group(1))
        member = channel.get_member(snowflake)

        return f"@{member.nick or member.name}"

    finalmsg = MENTION_RE.sub(user_replace, finalmsg)

    await channel.send(finalmsg)


def sentences(words: str) -> Iterable[str]:
    last = 0
    for match in SENTENCE_RE.finditer(words):
        string = words[last:match.start()].strip()
        if string:
            yield string

        last = match.end()

    if last < len(words):
        string = words[last:].strip()
        if string:
            yield string
