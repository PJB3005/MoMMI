from ..config import get_config
from ..commands import always_command, command
from ..client import client
from collections import defaultdict
import os
import re
import pickle
import logging
import random


logger = logging.getLogger(__name__)

if not os.path.isfile("markovdb"):
    open("markovdb", "a").close()

def zero():
    return 0

def zero_dict():
    return defaultdict(zero)

sentence_re = re.compile("([.,?\n]|(?<!@)!)")

class Chain(object):
    def __init__(self, filename):
        self.db = None
        self.filename = filename
        with open(filename, "rb") as f:
            try:
                self.db = pickle.load(f)
            except EOFError:
                logger.exception("Unable to load markov database.")
                self.db = defaultdict(zero_dict)

    def dump(self):
        try:
            with open(self.filename, "wb") as f:
                pickle.dump(self.db, f)
        except:
            logger.exception("Unable to dump markov database.")

    def read(self, words):
        for sentence in self.sentences(words):
            words = sentence.split()
            if len(words) < 7:
                continue

            last = ""

            for word in words:
                word = word.strip()
                chain = self.db[last]
                chain[word] += 1
                last = word

            self.db[last][""] += 1

    def sentences(self, words):
        last = 0
        for match in sentence_re.finditer(words):
            string = words[last:match.start()].strip()
            if string:
                yield string

            last = match.end()  

        if last < len(words):
            string = words[last:].strip()
            if string:
                yield string

    def generate(self, seed=""):
        message = []
        if seed != "":
            message.append(seed.title())

        for i in range(100): # Prevent infinite loop.
            # Basic pickweight based on https://stackoverflow.com/questions/3679694/a-weighted-version-of-random-choice
            chain = self.db[seed]
            logger.info(chain)
            total = sum(chain.values())
            picked = random.randint(0, total)

            for word in chain.keys():
                picked -= chain[word]
                if picked <= 0:
                    seed = word
                    break

            message.append(seed) 

            if seed == "":
                break
        
        logger.info(message)
        return " ".join(message) + "."

markov_chain = Chain("markovdb")

@always_command(True)
async def markov_reader(message):
    markov_chain.read(message.content)

@command("markov")
async def markov(content, match, message):
    await client.send_message(message.channel, markov_chain.generate())

def unload():
    markov_chain.dump()