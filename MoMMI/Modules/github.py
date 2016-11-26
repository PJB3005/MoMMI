import aiohttp
import asyncio
import json
import logging
import re
from discord import Colour, Embed
from ..commloop import comm_event
from ..client import client
from ..util import getchannel, getserver
from ..config import get_config


logger = logging.getLogger(__name__)
event_handlers = {}

COLOR_GITHUB_RED = Colour(0xFF4444)
COLOR_GITHUB_GREEN = Colour(0x6CC644)
COLOR_GITHUB_PURPLE = Colour(0x6E5494)
MAX_BODY_LENGTH = 200
MD_COMMENT_RE = re.compile(r"<!--.*-->", flags=re.DOTALL)


@comm_event
async def github_event(msg, address):
    if msg["id"] != "github":
        return

    logger.info("Handling message from GitHub.")
    logger.info(msg["event"])
    func = event_handlers.get(msg["event"])
    if not func:
        return

    await func(msg["content"])

invalid_actions = {"labeled", "assigned", "unassigned", "edited", "unlabeled", "synchronize"}
async def issues(msg):
    if msg["action"] in invalid_actions:
        return

    issue = msg["issue"]
    sender = msg["sender"]
    repository = msg["repository"]
    pre = None
    embed = Embed()
    if msg["action"] == "closed":
        pre = "<:ISSclosed:246037286322569216>"
        embed.colour = COLOR_GITHUB_RED
    else:
        pre = "<:ISSopened:246037149873340416>"
        embed.colour = COLOR_GITHUB_GREEN

    embed.title = pre + issue["title"]
    embed.url = issue["html_url"]
    embed.set_author(name=sender["login"], url=sender["url"], icon_url=sender["avatar_url"])
    embed.set_footer(text="{}#{} by {}".format(repository["full_name"], issue["number"], issue["user"]["login"]), icon_url=issue["user"]["avatar_url"])
    if len(issue["body"]) > MAX_BODY_LENGTH:
        embed.description = issue["body"][:MAX_BODY_LENGTH] + "..."
    else:
        embed.description = issue["body"]

    embed.description += "\n\u200B"

    channel = client.get_channel(str(get_config("mainserver.channels.code")))
    if not channel:
        logger.error("No channel.")

    await client.send_message(channel, embed=embed)


event_handlers["issues"] = issues

async def pr(msg):
    if msg["action"] == "synchronize" or msg["action"] == "opened":
        await secret_repo_check(msg)

    if msg["action"] in invalid_actions:
        return

    pull_request = msg["pull_request"]
    sender = msg["sender"]
    repository = msg["repository"]
    pre = None
    embed = Embed()
    if msg["action"] == "closed":
        pre = "<:PRclosed:246037149839917056>"
        embed.colour = COLOR_GITHUB_RED

    else:
        pre = "<:PRopened:245910125041287168>"
        embed.colour = COLOR_GITHUB_GREEN

    if msg["action"] == "closed" and pull_request["merged"]:
        pre = "<:PRmerged:245910124781240321>"
        embed.colour = COLOR_GITHUB_PURPLE

    embed.title = pre + pull_request["title"]
    embed.url = pull_request["html_url"]
    embed.set_author(name=sender["login"], url=sender["url"], icon_url=sender["avatar_url"])
    embed.set_footer(text="{}#{} by {}".format(repository["full_name"], pull_request["number"], pull_request["user"]["login"]), icon_url=pull_request["user"]["avatar_url"])

    new_body = MD_COMMENT_RE.sub("", pull_request["body"])  # type: str
    if len(new_body) > MAX_BODY_LENGTH:
        embed.description = new_body[:MAX_BODY_LENGTH] + "..."
    else:
        embed.description = new_body
    embed.description += "\n\u200B"

    channel = client.get_channel(str(get_config("mainserver.channels.code")))
    if not channel:
        logger.error("No channel.")

    await client.send_message(channel, embed=embed)

async def secret_repo_check(probject):
    headers = {"Authorization": "token %s" % (get_config("github.login.token"))}
    async with aiohttp.ClientSession() as session:
        url = probject["pull_request"]["url"] + "/files"
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                logger.error("Query to GitHub for PR file list returned status code %s!")
                return

            found = False
            content = await resp.text()
            logger.debug("Got back from GitHub for the files of PR #%s: %s", probject["number"], content)
            data = json.loads(content)
            for fileobject in data:
                if fileobject["filename"] in get_config("github.repo.secret_repo_files"):
                    found = True
                    break

            if found:
                url = probject["pull_request"]["issue_url"] + "/labels"
                postdata = json.dumps([get_config("github.repo.labels.secret_conflict")])
                async with session.post(url, data=postdata, headers=headers) as postresp:
                    logger.info("Setting label %s on PR #%s returned status code %s!", get_config("github.repo.secret_repo_files"), probject["number"], postresp.status)

event_handlers["pull_request"] = pr
