import aiohttp
import asyncio
import json
import logging
import re
import os
import subprocess
from colorhash import ColorHash
from discord import Colour, Embed, Message
from typing import re as re_type, List
from urllib.parse import quote
from ..commloop import comm_event
from ..client import client
from ..util import getchannel, getserver
from ..config import get_config
from ..commands import always_command, command
from .irc import irc_transform, prevent_ping

logger = logging.getLogger(__name__)
event_handlers = {}

# Taken from https://github.com/d3athrow/vgstation13/blob/Bleeding-Edge/bot/plugins/GitHub.py
REG_PATH = re.compile(r"\[([a-zA-Z\-_/][a-zA-Z0-9\- _/]*\.[a-zA-Z]+)(#L\d+(?:-L\d+)?)?\]", re.I)
REG_ISSUE = re.compile(r"\[#?([0-9]+)\]")
REG_BRACKETS = re.compile(r"\[(.+?)\]")

COLOR_GITHUB_RED = Colour(0xFF4444)
COLOR_GITHUB_GREEN = Colour(0x6CC644)
COLOR_GITHUB_PURPLE = Colour(0x6E5494)
MAX_BODY_LENGTH = 200
MD_COMMENT_RE = re.compile(r"<!--.*-->", flags=re.DOTALL)
HEADERS = {"Authorization": "token %s" % (get_config("github.login.token"))}


@comm_event
async def github_event(msg):
    if msg["type"] != "github":
        return
    msg = msg["cont"]

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
    embed.set_author(name=sender["login"], url=sender["html_url"], icon_url=sender["avatar_url"])
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
    embed.set_author(name=sender["login"], url=sender["html_url"], icon_url=sender["avatar_url"])
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
    async with aiohttp.ClientSession() as session:
        url = probject["pull_request"]["url"] + "/files"
        async with session.get(url, headers=HEADERS) as resp:
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
                async with session.post(url, data=postdata, headers=HEADERS) as postresp:
                    logger.info("Setting label %s on PR #%s returned status code %s!", get_config("github.repo.secret_repo_files"), probject["number"], postresp.status)

event_handlers["pull_request"] = pr


# handling of stuff like [2000] and [world.dm]
def github_url(sub: str) -> str:
    return "https://api.github.com" + sub


def colour_extension(filename: str) -> Colour:
    ext = filename.split(".")[-1]
    c = ColorHash(ext)
    return Colour(int(c.hex[1:], 16))


# Indent 2: the indent
@always_command()
async def issue(message: Message):
    async with aiohttp.ClientSession() as session:
        for match in REG_ISSUE.finditer(message.content):
            id = int(match.group(1))
            if id < 1000:
                continue

            url = github_url("/repos/{}/{}/issues/{}".format(get_config("github.repo.owner"), get_config("github.repo.name"), id))
            async with session.get(url, headers=HEADERS) as resp:
                content = json.loads(await resp.text())

            # God forgive me.
            embed = Embed()
            emoji = ""
            if content.get("pull_request") is not None:
                if content["state"] == "open":
                    emoji = "<:PRopened:245910125041287168>"
                    embed.colour = COLOR_GITHUB_GREEN
                else:
                    url = github_url("/repos/{}/{}/pulls/{}".format(get_config("github.repo.owner"), get_config("github.repo.name"), id))
                    async with session.get(url, headers=HEADERS) as resp:
                        prcontent = json.loads(await resp.text())
                        if prcontent["merged"]:
                            emoji = "<:PRmerged:245910124781240321>"
                            embed.colour = COLOR_GITHUB_PURPLE
                        else:
                            emoji = "<:PRclosed:246037149839917056>"
                            embed.colour = COLOR_GITHUB_RED

            else:
                if content["state"] == "open":
                    emoji = "<:ISSopened:246037149873340416>"
                    embed.colour = COLOR_GITHUB_GREEN
                else:
                    emoji = "<:ISSclosed:246037286322569216>"
                    embed.colour = COLOR_GITHUB_RED

            embed.title = emoji + content["title"]
            embed.url = content["html_url"]
            embed.set_footer(text="{}/{}#{} by {}".format(get_config("github.repo.owner"), get_config("github.repo.name"), content["number"], content["user"]["login"]), icon_url=content["user"]["avatar_url"])
            if len(content["body"]) > MAX_BODY_LENGTH:
                embed.description = content["body"][:MAX_BODY_LENGTH] + "..."
            else:
                embed.description = content["body"]
            embed.description += "\n\u200B"

            await client.send_message(message.channel, embed=embed)

        if REG_PATH.search(message.content):
            url = github_url("/repos/{}/{}/branches/{}".format(get_config("github.repo.owner"), get_config("github.repo.name"), get_config("github.repo.branch")))
            async with session.get(url, headers=HEADERS) as resp:
                branch = json.loads(await resp.text())

            url = github_url("/repos/{}/{}/git/trees/{}".format(get_config("github.repo.owner"), get_config("github.repo.name"), branch["commit"]["sha"]))
            async with session.get(url, headers=HEADERS, params={"recursive": 1}) as resp:
                tree = json.loads(await resp.text())

            paths = []  # type: List[str]
            for match in REG_PATH.finditer(message.content):
                path = match.group(1).lower()
                logger.info(path)
                paths.append(path)

            for hash in tree["tree"]:
                # logger.debug(hash["path"])

                for path in paths:
                    if hash["path"].lower().endswith(path):
                        thepath = hash["path"]  # type: str
                        html_url = "https://github.com/{}/{}".format(get_config("github.repo.owner"), get_config("github.repo.name"))
                        logger.info(html_url)
                        logger.info(get_config("github.repo.branch"))
                        logger.info(quote(thepath))
                        logger.info(match.group(2))
                        url = "%s/blob/%s/%s" % (html_url, get_config("github.repo.branch"), quote(thepath)) + (match.group(2) or "")

                        embed = Embed()
                        embed.colour = colour_extension(thepath)
                        embed.set_footer(text="{}/{}".format(get_config("github.repo.owner"), get_config("github.repo.name")))
                        embed.url = url
                        embed.title = thepath.split("/")[-1]
                        embed.description = "`{}`".format(thepath)

                        await client.send_message(message.channel, embed=embed)
                        paths.remove(path)


def replace_brackets(match: re_type.Match) -> str:
    if len(match.group(1)) < 2:
        return "[{}]".format(match.group(1))

    return "[{}]".format(prevent_ping(match.group(1)))


def filter_issue_brackets(message, author, discord_server, irc_client):
    return REG_BRACKETS.sub(replace_brackets, message)


async def load():
    irc_transform(filter_issue_brackets)


@command(r"testmerge\s*\[?(\d+)\]?", role=get_config("mainserver.roles.collab"))
async def test_merger(content, match, message):
    from asyncio import create_subprocess_exec
    logger.info("I did not break!")
    id = int(match.group(1))
    async with aiohttp.ClientSession() as session:
        # GET /repos/:owner/:repo/pulls/:number
        url = github_url(f"/repos/{get_config('github.repo.owner')}/{get_config('github.repo.name')}/pulls/{id}")

        async with session.get(url, headers=HEADERS) as resp:
            if resp.status != 200:
                await client.send_message(message.channel, f"❌ Unable to fetch information for PR {id}.")
                return

            content = json.loads(await resp.text())

        if content["merged"] == True:
            await client.send_message(message.channel, "❌ This PR has already been merged!")
            return

        if content["mergeable"] != True:
            await client.send_message(message.channel, "❌ This PR is conflicting and cannot be test merged.")
            return

        await client.send_message(message.channel, "⌛ Test merging PR...")

        origin_uri = f"git@github.com:{get_config('github.repo.owner')}/{get_config('github.repo.name')}.git"
        HEAD_URI = content['head']['repo']['git_url']
        BRANCH = content['head']['ref']

        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_SSH_COMMAND"] = f"ssh -i {get_config('github.ssh-key')}"

        kwargs = {
            "cwd": get_config("github.testmerge"),
            "env": env,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE
        }

        commands = [
            create_subprocess_exec("git", "fetch", "origin", **kwargs),
            create_subprocess_exec("git", "reset", "--hard",  **kwargs),
            create_subprocess_exec("git", "checkout", "-B", "testserver", "origin/Bleeding-Edge",  **kwargs),
            create_subprocess_exec("git", "pull", HEAD_URI, BRANCH, "--no-edit", **kwargs),
            create_subprocess_exec("git", "push", "-f", origin_uri, "testserver",  **kwargs)
        ]

        index = 1
        for command in commands:
            logger.info(f"fuck: {index}")
            process = await command
            await process.wait()
            if process.returncode != 0:
                out = (await process.stdout.read()).decode("UTF-8")
                err = (await process.stderr.read()).decode("UTF-8")
                await client.send_message(message.channel, f"❌ Git command #{index} returned bad status code `{process.returncode}`. Uh oh!")
                logger.error(f"Git command #{index} failed: {process.returncode}.\nstdout:\n{out}\nstderr:\n{err}")
                return

            index += 1

        await client.send_message(message.channel, f"✅ PR testmerge success. `{get_config('github.testmerge-address')}` will be up soon.")
