from ..commloop import comm_event
from ..client import client
from ..util import getchannel, getserver
from ..config import get_config
import logging
import asyncio
import aiohttp
import json

logger = logging.getLogger(__name__)
event_handlers = {}


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
        logger.error("invalid")
        return

    logger.info("yes")

    issue = msg["issue"]
    sender = msg["sender"]
    pre = None
    if msg["action"] == "closed":
        pre = "<:ISSclosed:246037286322569216>"
    else:
        pre = "<:ISSopened:246037149873340416>"

    message = "\u200B%s Issue #%s **%s** by %s: %s" % (pre, issue["number"], msg["action"], sender["login"], issue["html_url"])

    channel = client.get_channel(str(get_config("mainserver.channels.code")))
    if not channel:
        logger.error("No channel.")

    await client.send_message(channel, message)


event_handlers["issues"] = issues

async def pr(msg):
    if msg["action"] == "synchronize" or msg["action"] == "opened":
        await secret_repo_check(msg)

    if msg["action"] in invalid_actions:
        return

    pull_request = msg["pull_request"]
    sender = msg["sender"]
    action = msg["action"]
    if msg["action"] == "closed":
        pre = "<:PRclosed:246037149839917056>"
    else:
        pre = "<:PRopened:245910125041287168>"

    if action == "closed" and pull_request["merged"]:
        action = "merged"
        pre = "<:PRmerged:245910124781240321>"

    message = "\u200B%s Pull Request #%s **%s** by %s: %s" % (pre, pull_request["number"], action, sender["login"], pull_request["html_url"])

    channel = client.get_channel(str(get_config("mainserver.channels.code")))
    if not channel:
        logger.error("No channel.")

    await client.send_message(channel, message)

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
