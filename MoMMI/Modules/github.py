import json
import logging
import re
import asyncio
from typing import re as typing_re, Dict, Any, Tuple, List, Optional
from urllib.parse import quote
import aiohttp
from colorhash import ColorHash
from discord import Colour, Embed, Message, User
from MoMMI.commloop import comm_event
from MoMMI.commands import always_command
from MoMMI.server import MChannel
from MoMMI.master import master
from MoMMI.Modules.irc import irc_transform

logger = logging.getLogger(__name__)

REG_PATH = re.compile(r"\[(.+?)(?:(?::|#L)(\d+)(?:-L?(\d+))?)?\]", re.I)
REG_ISSUE = re.compile(r"\[#?([0-9]+)\]")
REG_COMMIT = re.compile(r"\[([0-9a-f]{40})\]", re.I)

COLOR_GITHUB_RED = Colour(0xFF4444)
COLOR_GITHUB_GREEN = Colour(0x6CC644)
COLOR_GITHUB_PURPLE = Colour(0x6E5494)
MAX_BODY_LENGTH = 200
MD_COMMENT_RE = re.compile(r"<!--.*-->", flags=re.DOTALL)
DISCORD_CODEBLOCK_RE = re.compile(r"```(?:([^\n]*)\n)?(.*)```", flags=re.DOTALL)

GITHUB_SESSION = "github_session"

async def load(loop: asyncio.AbstractEventLoop):
    if not master.has_cache(GITHUB_SESSION):
        headers = {"Authorization": f"token {master.config.get_module('github.token')}"}
        session = aiohttp.ClientSession(headers=headers)
        master.set_cache(GITHUB_SESSION, session)


async def shutdown(loop: asyncio.AbstractEventLoop):
    master.get_cache(GITHUB_SESSION).close()
    master.del_cache(GITHUB_SESSION)


def github_url(sub: str) -> str:
    return f"https://api.github.com{sub}"


def colour_extension(filename: str) -> Colour:
    ext = filename.split(".")[-1]
    c = ColorHash(ext)
    return Colour(int(c.hex[1:], 16))


@comm_event("github_event")
async def github_event(channel: MChannel, message, meta):
    event = message['event']
    logger.debug(f"Handling GitHub event '$YELLOW{event}$RESET' to '$YELLOW{meta}$RESET'")

    # Find a function by the name of `on_github_{event}` in globals and call it.
    func = globals().get(f"on_github_{event}")
    if func is None:
        logger.debug("No handler for this event, ignoring.")
        return

    await func(channel, message["data"], meta)


async def on_github_push(channel: MChannel, message, repo):
    embed = Embed()
    embed.set_author(name=message["sender"]["login"], url=message["sender"]["html_url"], icon_url=message["sender"]["avatar_url"])
    embed.set_footer(text=repo)
    embed.title = "New commits"

    content = ""
    for commit in message["commits"]:
        message = commit["message"]
        if len(message) > 67:
            message = message[:67] + "..."
        content += f"`{commit['id'][:7]}` {message}\n"

    embed.description = content

    await channel.send(embed=embed)

async def on_github_issues(channel, message, repo):
    logger.debug("yes")


# Indent 2: the indent
# handling of stuff like [2000] and [world.dm]
@always_command("github_issue")
async def issue(channel: MChannel, match: typing_re.Match, message: Message):
    try:
        cfg = channel.server_config("modules.github")
    except:
        # Server has no config settings for GitHub.
        return

    repo = cfg["repo"]
    branchname = cfg["branch"]
    session = master.get_cache(GITHUB_SESSION)

    for match in REG_ISSUE.finditer(message.content):
        issueid = int(match.group(1))
        if issueid < 30:
            continue

        url = github_url(f"/repos/{repo}/issues/{issueid}")
        async with session.get(url) as resp:
            content = await resp.json()

        # God forgive me.
        embed = Embed()
        emoji = ""
        if content["state"] == "open":
            if content.get("pull_request") is not None:
               emoji = "<:PRopened:245910125041287168>"
            else:
               emoji = "<:ISSopened:246037149873340416>"
            embed.colour = COLOR_GITHUB_GREEN

        elif content.get("pull_request") is not None:
            url = github_url(f"/repos/{repo}/pulls/{issueid}")
            async with session.get(url) as resp:
                prcontent = await resp.json()
                if prcontent["merged"]:
                    emoji = "<:PRmerged:245910124781240321>"
                    embed.colour = COLOR_GITHUB_PURPLE
                else:
                    emoji = "<:PRclosed:246037149839917056>"
                    embed.colour = COLOR_GITHUB_RED

        else:
            emoji = "<:ISSclosed:246037286322569216>"
            embed.colour = COLOR_GITHUB_RED

        embed.title = emoji + content["title"]
        embed.url = content["html_url"]
        embed.set_footer(text=f"{repo}#{content['number']} by {content['user']['login']}", icon_url=content["user"]["avatar_url"])
        if len(content["body"]) > MAX_BODY_LENGTH:
            embed.description = content["body"][:MAX_BODY_LENGTH] + "..."
        else:
            embed.description = content["body"]
        embed.description += "\n\u200B"

        await channel.send(embed=embed)

    if REG_PATH.search(message.content):
        url = github_url(f"/repos/{repo}/branches/{branchname}")
        async with session.get(url) as resp:
            branch = json.loads(await resp.text())

        url = github_url(f"/repos/{repo}/git/trees/{branch['commit']['sha']}")
        async with session.get(url, params={"recursive": 1}) as resp:
            tree = json.loads(await resp.text())

        paths: List[Tuple[str, Optional[int], Optional[int]]]
        paths = []
        for match in REG_PATH.finditer(message.content):
            path = match.group(1).lower()
            # Ignore tiny paths, too common accidentally in code blocks.
            if len(path) <= 3:
                continue

            linestart = None
            lineend = None
            if match.group(2):
                linestart = match.group(2)
                if match.group(3):
                    lineend = match.group(3)

            paths.append((path, linestart, lineend))

        for filehash in tree["tree"]:
            for path, linestart, lineend in paths:
                if not filehash["path"].lower().endswith(path):
                    continue

                thepath = filehash["path"]  # type: str
                html_url = f"https://github.com/{repo}"
                file_url_part = quote(thepath)
                if linestart is not None:
                    file_url_part += f"#L{linestart}"
                    if lineend is not None:
                        file_url_part += f"-L{lineend}"

                url = f"{html_url}/blob/{branchname}/{file_url_part}"
                title = thepath.split("/")[-1]
                if lineend is not None:
                    title += f" lines {linestart}-{lineend}"

                elif linestart is not None:
                    title += f" line {linestart}"

                embed = Embed()
                embed.colour = colour_extension(thepath)
                embed.set_footer(text=f"{repo}")
                embed.url = url
                embed.title = title

                embed.description = f"`{thepath}`"

                await channel.send(embed=embed)

                paths.remove((path, linestart, lineend))

    for match in REG_COMMIT.finditer(message.content):
        sha = match.group(1)
        url = github_url(f"/repos/{repo}/git/commits/{sha}")
        async with session.get(url) as resp:
            if resp.status != 200:
                continue

            commit = await resp.json()

        split = commit["message"].split("\n")
        title = split[0]
        desc = "\n".join(split[1:])
        if len(desc) > MAX_BODY_LENGTH:
            desc = desc[:MAX_BODY_LENGTH] + "..."

        embed = Embed()
        embed.set_footer(text=f"{repo} {sha} by {commit['author']['name']}")
        embed.url = commit["html_url"]
        embed.title = title
        embed.description = desc

        await channel.send(embed=embed)


@irc_transform("convert_code_blocks")
async def convert_code_blocks(message: str, author: User, irc_client, discord_server):
    try:
        last = 0
        out = ""
        # print("yes!")
        for match in DISCORD_CODEBLOCK_RE.finditer(message):
            # print("my man!")
            out += message[last:match.start()]

            gist_contents = ""
            extension = "txt"
            # Has a space on first line of code block (the ``` line).
            # Read first line as part of the contents.
            language = match.group(1)
            if language is None or language == "":
                pass

            elif " " in language.strip() or match.group(2).strip() == "":
                gist_contents = match.group(1)

            else:
                extension = language.strip()

            gist_contents += match.group(2).strip()

            url = await make_gist(gist_contents, f"file.{extension}", f"Code snippet from Discord -> IRC relay.")

            out += url
            last = match.end()

        out += message[last:len(message)]

        return out

    except:
        logger.exception("Failed to turn code block into gist.")
        return "<MoMMI error tell PJB>"


async def make_gist(contents: str, name: str, desc: str):
    session = master.get_cache(GITHUB_SESSION)

    # POST /gists
    url = github_url("/gists")
    post_data = {
        "description": desc,
        "public": False,
        "files": {
            name: {
                "content": contents
            }
        }
    }
    async with session.post(url, data=json.dumps(post_data)) as resp:
        if resp.status != 201:
            return f"[GIST ERROR: {resp.status} ({resp.reason})]"

        output = await resp.json()
        return output["html_url"]
