import logging
import re
from urllib.parse import quote
from github3 import login
from ..client import client
from ..commands import always_command
from ..config import get_config


logger = logging.getLogger(__name__)
github = login(token=get_config("github.login.token"))
repo   = github.repository(get_config("github.repo.owner"), get_config("github.repo.name"))
tree   = tree = repo.tree(repo.branch(get_config("github.repo.branch")).commit.sha).recurse()

# Taken from https://github.com/d3athrow/vgstation13/blob/Bleeding-Edge/bot/plugins/GitHub.py
REG_PATH = re.compile(r"\[([a-zA-Z\-_/][a-zA-Z0-9\- _/]*\.[a-zA-Z]+)(#L\d+(?:-L\d+)?)?\]", re.I)
REG_ISSUE = re.compile(r"\[#?([0-9]+)\]")

@always_command()
async def issue(message):
    for match in REG_ISSUE.finditer(message.content):
        id = int(match.group(1))
        issue = repo.issue(id)

        await client.send_message(message.channel, issue.html_url)
    

    for match in REG_PATH.finditer(message.content):
        path = match.group(1).lower()
        logger.info(path)
        length = -len(path)
        for hash in tree.tree:
            logger.info(hash.path)
            if hash.path.lower()[length:] == path:
                url = "%s/blob/%s/%s" % (repo.html_url, get_config("github.repo.branch"), quote(hash.path)) + match.group(2)
                await client.send_message(message.channel, url)
                break;

def update():
    global tree
    repo.refresh()

    tree = repo.tree(repo.branch(get_config("github.repo.branch")).commit.sha)
    tree.recurse()