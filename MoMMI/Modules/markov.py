import logging
import random
import re
from collections import defaultdict
from typing import DefaultDict, Match, Iterable
from discord import Message
from MoMMI.commands import command, always_command
from MoMMI.server import MChannel

SENTENCE_RE = re.compile(r"([.,?\n]|(?<!@)!)")
PARENT_RE = re.compile(r"[[\]{}()\"']")
CHAIN_TYPE = DefaultDict[str, DefaultDict[str, int]]

logger = logging.getLogger(__name__)


@always_command("markov_read")
async def markov_reader(channel: MChannel, match: Match, message: Message):
    # if not isbanned(message.author, bantypes.markov):

    content = PARENT_RE.sub("", message.content.lower())
    # Because chain is a referenced object.
    # We do not need to reset it explicitly.
    chain: CHAIN_TYPE
    try:
        chain = channel.get_storage("markov")
    except KeyError:
        chain = defaultdict(lambda: defaultdict(int))
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


@command("markov", r"markov\s*(?:\((\S*)\))?")
async def markov(channel: MChannel, match: Match, message: Message):
    try:
        chain = channel.get_storage("markov")
    except:
        return

    message = None
    seed = match.group(1) or ""
    if seed not in chain:
        await channel.send("Cannot make markov chain: unknown word.")
        return

    # Repeat to try to prevent short chains.
    for _ in range(5):
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

    await channel.send(" ".join(message) + ".")


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
