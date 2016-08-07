from .commloop import comm_event
from ..client import client
from ..util import getchannel, getserver
import logging
import asyncio


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

invalid_actions = ["labeled", "assigned", "unassigned", "edited", "unlabeled", "synchronize"]
async def issues(msg):
    if msg["action"] in invalid_actions:
        return

    issue = msg["issue"]
    sender = msg["sender"]
    message = "Issue #%s **%s** by %s: %s" % (issue["number"], msg["action"], sender["login"], issue["html_url"])
    
    channel = getchannel(getserver(client, "/vg/"), "code-map-sprite")
    if not channel:
        logger.error("No channel.")

    await client.send_message(channel, message)
    

event_handlers["issues"] = issues

async def pr(msg):
    if msg["action"] in invalid_actions:
        return

    pull_request = msg["pull_request"]
    sender = msg["sender"]
    action = msg["action"]
    if action == "closed" and pull_request["merged"]:
        action = "merged"

    message = "Pull Request #%s **%s** by %s: %s" % (pull_request["number"], action, sender["login"], pull_request["html_url"])
    
    channel = getchannel(getserver(client, "/vg/"), "code-map-sprite")
    if not channel:
        logger.error("No channel.")

    await client.send_message(channel, message)

event_handlers["pull_request"] = pr