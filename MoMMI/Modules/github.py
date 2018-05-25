import json
import logging
import re
import asyncio
from typing import re as typing_re, Tuple, List, Optional, Any, Set, Dict, DefaultDict
from urllib.parse import quote, quote_plus
from collections import defaultdict
import aiohttp
from colorhash import ColorHash
from discord import Color, Embed, Message, User
from MoMMI.commloop import comm_event, global_comm_event
from MoMMI.commands import always_command
from MoMMI.channel import MChannel
from MoMMI.master import master
from MoMMI.Modules.irc import irc_transform

logger = logging.getLogger(__name__)

REG_PATH = re.compile(r"\[(.+?)(?:(?::|#L)(\d+)(?:-L?(\d+))?)?\]", re.I)
REG_ISSUE = re.compile(r"\[#?([0-9]+)\]")
REG_COMMIT = re.compile(r"\[([0-9a-f]{40})\]", re.I)

COLOR_GITHUB_RED = Color(0xFF4444)
COLOR_GITHUB_GREEN = Color(0x6CC644)
COLOR_GITHUB_PURPLE = Color(0x6E5494)
MAX_BODY_LENGTH = 500
MAX_COMMIT_LENGTH = 67
MD_COMMENT_RE = re.compile(r"<!--.*-->", flags=re.DOTALL)
DISCORD_CODEBLOCK_RE = re.compile(
    r"```(?:([^\n]*)\n)?(.*)```", flags=re.DOTALL)

GITHUB_SESSION = "github_session"
GITHUB_CACHE = "github_cache"

GITHUB_ISSUE_MAX_MESSAGES = 5

VALID_ISSUES_ACTIONS = {"opened", "closed", "reopened"}

KNOWN_MERGE_COMMITS: Set[str] = set()


async def load(loop: asyncio.AbstractEventLoop):
    if not master.has_cache(GITHUB_SESSION):
        headers = {
            "Authorization": f"token {master.config.get_module('github.token')}",
            "User-Agent": "MoMMIv2 (@PJBot, @PJB3005)",
            "Accept": "application/vnd.github.v3+json",
        }
        session = aiohttp.ClientSession(headers=headers)
        master.set_cache(GITHUB_SESSION, session)

    if not master.has_cache(GITHUB_CACHE):
        master.set_cache(GITHUB_CACHE, {})


async def shutdown(loop: asyncio.AbstractEventLoop):
    master.get_cache(GITHUB_SESSION).close()
    master.del_cache(GITHUB_SESSION)


def github_url(sub: str) -> str:
    return f"https://api.github.com{sub}"


def colour_extension(filename: str) -> Color:
    ext = filename.split(".")[-1]
    c = ColorHash(ext)
    return Color(int(c.hex[1:], 16))


@comm_event("github")
async def github_event(channel: MChannel, message, meta):
    event = message['event']
    logger.debug(
        f"Handling GitHub event '$YELLOW{event}$RESET' to '$YELLOW{meta}$RESET'")

    # Find a function by the name of `on_github_{event}` in globals and call it.
    func = globals().get(f"on_github_{event}")
    if func is None:
        logger.debug("No handler for this event, ignoring.")
        return

    asyncio.ensure_future(func(channel, message["content"], meta))


async def on_github_push(channel: MChannel, message: Any, meta: str):
    commits = message["commits"]
    if not commits:
        return

    # We need to sleep for a few because
    # the PR event needs to update commit hashes to ignore
    # and it does a network request.
    await asyncio.sleep(3)

    embed = Embed()
    embed.url = message["compare"]
    embed.set_author(name=message["sender"]["login"], url=message["sender"]
                     ["html_url"], icon_url=message["sender"]["avatar_url"])
    embed.set_footer(text=message["repository"]["full_name"])
    commits_count = ""
    if len(commits) == 1:
        commits_count = "**1** New Commit"
    else:
        commits_count = f"**{len(commits)}** New Commits"

    embed.title = f"{commits_count} to **{message['ref']}**"

    if message["forced"]:
        embed.title = f"[FORCE PUSHED] {embed.title}"
        embed.color = Color(0xFF0000)

    content = ""

    found = False
    count = 0
    for commit in commits:
        message = commit["message"]
        # Don't do these to reduce spam.
        if message != "[ci skip] Automatic changelog update." and commit["id"] not in KNOWN_MERGE_COMMITS:
            found = True

        if len(message) > 67:
            message = message[:67] + "..."
        content += f"[`{commit['id'][:7]}`]({commit['url']}) {message}\n"
        count += 1
        if count > 10:
            content += "<.....>"
            break

    if not found:
        return

    embed.description = content

    await channel.send(embed=embed)


async def on_github_issues(channel: MChannel, message, meta):
    if message["action"] not in VALID_ISSUES_ACTIONS:
        return

    issue = message["issue"]
    sender = message["sender"]
    repository = message["repository"]
    pre = None
    embed = Embed()
    if message["action"] == "closed":
        pre = "<:ISSclosed:246037286322569216>"
        embed.color = COLOR_GITHUB_RED
    else:
        pre = "<:ISSopened:246037149873340416>"
        embed.color = COLOR_GITHUB_GREEN

    embed.title = pre + issue["title"]
    embed.url = issue["html_url"]
    embed.set_author(
        name=sender["login"], url=sender["html_url"], icon_url=sender["avatar_url"])
    embed.set_footer(text="{}#{} by {}".format(
        repository["full_name"], issue["number"], issue["user"]["login"]), icon_url=issue["user"]["avatar_url"])
    if len(issue["body"]) > MAX_BODY_LENGTH:
        embed.description = issue["body"][:MAX_BODY_LENGTH] + "..."
    else:
        embed.description = issue["body"]

    embed.description += "\n\u200B"

    await channel.send(embed=embed)


async def on_github_pull_request(channel: MChannel, message: Any, meta: str):
    action = message["action"]
    if action not in VALID_ISSUES_ACTIONS:
        return

    pull_request = message["pull_request"]
    sender = message["sender"]
    repository = message["repository"]
    pre = None

    embed = Embed()
    if action == "closed":
        pre = "<:PRclosed:246037149839917056>"
        embed.color = COLOR_GITHUB_RED

    else:
        pre = "<:PRopened:245910125041287168>"
        embed.color = COLOR_GITHUB_GREEN

    if action == "closed" and pull_request["merged"]:
        pre = "<:PRmerged:437316952772444170>"
        embed.color = COLOR_GITHUB_PURPLE
        KNOWN_MERGE_COMMITS.add(pull_request["merge_commit_sha"])
        asyncio.ensure_future(add_known_merge_commits(
            repository["full_name"], pull_request["number"]))

    embed.title = pre + pull_request["title"]
    embed.url = pull_request["html_url"]
    embed.set_author(
        name=sender["login"], url=sender["html_url"], icon_url=sender["avatar_url"])
    embed.set_footer(text="{}#{} by {}".format(
        repository["full_name"], pull_request["number"], pull_request["user"]["login"]), icon_url=pull_request["user"]["avatar_url"])

    new_body = MD_COMMENT_RE.sub("", pull_request["body"])
    if len(new_body) > MAX_BODY_LENGTH:
        embed.description = new_body[:MAX_BODY_LENGTH] + "..."
    else:
        embed.description = new_body
    embed.description += "\n\u200B"

    await channel.send(embed=embed)


async def add_known_merge_commits(repo: str, number: int):
    url = github_url(f"/repos/{repo}/pulls/{number}/commits")
    commits = await get_github_object(url)
    for commit in commits:
        sha = commit["sha"]
        KNOWN_MERGE_COMMITS.add(sha)


async def on_github_issue_comment(channel: MChannel, message: Any, meta: str):
    if message["action"] != "created":
        return

    issue = message["issue"]
    comment = message["comment"]
    repo_name = message["repository"]["full_name"]

    if not channel.module_config(f"github.repos.{repo_name}.show_comments", True):
        return

    embed = Embed()
    embed.set_author(name=message["sender"]["login"], url=message["sender"]
                     ["html_url"], icon_url=message["sender"]["avatar_url"])
    embed.set_footer(
        text=f"{repo_name}#{issue['number']} by {issue['user']['login']}")
    embed.title = f"New Comment: {issue['title']}"
    embed.url = message["comment"]["html_url"]
    if len(comment["body"]) > MAX_BODY_LENGTH:
        embed.description = comment["body"][:MAX_BODY_LENGTH] + "..."
    else:
        embed.description = comment["body"]

    await channel.send(embed=embed)


@global_comm_event("secret_repo_pr_checker")
async def secret_repo_check(message: Any, meta: str):
    if "event" not in message or message["event"] != "pull_request":
        return

    message = message["content"]
    action = message["action"]
    if action != "synchronize" and action != "opened" and action != "reopened":
        return

    repo_name = message["repository"]["full_name"]
    conflict_files: List[str] = master.config.get_module(
        f"github.repos.{repo_name}.secret_repo_files", [])
    if not conflict_files:
        return

    files = await get_github_object(message["pull_request"]["url"] + "/files")
    found = False
    for fileobject in files:
        if fileobject["filename"] in conflict_files:
            found = True
            break

    label_name = master.config.get_module(f"github.repos.{repo_name}.labels.secret_conflicts", "Secret Repo Conflict")
    url = message["pull_request"]["issue_url"] + "/labels"
    labels = await get_github_object(url)
    haslabel = False
    for label in labels:
        if label["name"] == label_name:
            haslabel = True
            break

    if haslabel == found:
        return

    session: aiohttp.ClientSession = master.get_cache(GITHUB_SESSION)

    url = message["pull_request"]["issue_url"] + "/labels"

    session = master.get_cache(GITHUB_SESSION)
    if found:
        postdata = json.dumps(
            [label_name])
        async with session.post(url, data=postdata) as postresp:
            logger.info("Setting secret repo conflicts label on PR #%s returned status code %s!",
                        message["number"], postresp.status)
    else:
        async with session.delete(url + "/" + quote_plus(label_name)):
            logger.info("Deleting secret repo conflicts label on PR #%s returned status code %s!",
                        message["number"], postresp.status)

# Indent 2: the indent
# handling of stuff like [2000] and [world.dm]


@always_command("github_issue")
async def issue_command(channel: MChannel, match: typing_re.Match, message: Message):
    try:
        cfg = channel.server_config("modules.github.repos")
    except:
        # Server has no config settings for GitHub.
        return

    await try_handle_file_embeds(message.content, channel, cfg)

    for repo_config in cfg:
        repo = repo_config["repo"]

        for match in REG_ISSUE.finditer(message.content):
            issueid = int(match.group(1))
            if issueid < 30:
                continue

            url = github_url(f"/repos/{repo}/issues/{issueid}")
            content = await get_github_object(url)

            # God forgive me.
            embed = Embed()
            emoji = ""
            if content["state"] == "open":
                if content.get("pull_request") is not None:
                    emoji = "<:PRopened:245910125041287168>"
                else:
                    emoji = "<:ISSopened:246037149873340416>"
                embed.color = COLOR_GITHUB_GREEN

            elif content.get("pull_request") is not None:
                url = github_url(f"/repos/{repo}/pulls/{issueid}")
                prcontent = await get_github_object(url)
                if prcontent["merged"]:
                    emoji = "<:PRmerged:437316952772444170>"
                    embed.color = COLOR_GITHUB_PURPLE
                else:
                    emoji = "<:PRclosed:246037149839917056>"
                    embed.color = COLOR_GITHUB_RED

            else:
                emoji = "<:ISSclosed:246037286322569216>"
                embed.color = COLOR_GITHUB_RED

            embed.title = emoji + content["title"]
            embed.url = content["html_url"]
            embed.set_footer(
                text=f"{repo}#{content['number']} by {content['user']['login']}", icon_url=content["user"]["avatar_url"])
            if len(content["body"]) > MAX_BODY_LENGTH:
                embed.description = content["body"][:MAX_BODY_LENGTH] + "..."
            else:
                embed.description = content["body"]
            embed.description += "\n\u200B"

            await channel.send(embed=embed)

        for match in REG_COMMIT.finditer(message.content):
            sha = match.group(1)
            url = github_url(f"/repos/{repo}/git/commits/{sha}")
            try:
                commit = await get_github_object(url)
            except:
                continue

            split = commit["message"].split("\n")
            title = split[0]
            desc = "\n".join(split[1:])
            if len(desc) > MAX_BODY_LENGTH:
                desc = desc[:MAX_BODY_LENGTH] + "..."

            embed = Embed()
            embed.set_footer(
                text=f"{repo} {sha} by {commit['author']['name']}")
            embed.url = commit["html_url"]
            embed.title = title
            embed.description = desc

            await channel.send(embed=embed)


async def try_handle_file_embeds(message: str, channel: MChannel, cfg: List[Dict[str, str]]) -> bool:
    if not REG_PATH.search(message):
        return False

    paths: List[Tuple[str, Optional[str], Optional[str], bool]]
    paths = []
    for match in REG_PATH.finditer(message):
        path = match.group(1).lower()
        # Ignore tiny paths, too common accidentally in code blocks.
        if len(path) <= 3:
            continue

        rooted = False
        if path.startswith("^"):
            path = path[1:]
            rooted = True

        linestart = None
        lineend = None
        if match.group(2):
            linestart = match.group(2)
            if match.group(3):
                lineend = match.group(3)

        paths.append((path, linestart, lineend, rooted))

    # That's reponame: list((title, url))
    output: DefaultDict[str, List[Tuple[str, str]]] = defaultdict(list)

    for repocfg in cfg:
        repo = repocfg["repo"]
        branchname = repocfg["branch"]

        url = github_url(f"/repos/{repo}/branches/{branchname}")
        branch = await get_github_object(url)

        url = github_url(
            f"/repos/{repo}/git/trees/{branch['commit']['sha']}")
        tree = await get_github_object(url, params={"recursive": 1})

        for filehash in tree["tree"]:
            for path, linestart, lineend, rooted in paths:
                if rooted:
                    if not filehash["path"].lower().startswith(path):
                        continue

                else:
                    if not filehash["path"].lower().endswith(path):
                        continue

                thepath = filehash["path"]  # type: str
                file_url_part = quote(thepath)
                if linestart is not None:
                    file_url_part += f"#L{linestart}"
                    if lineend is not None:
                        file_url_part += f"-L{lineend}"

                url = f"https://github.com/{repo}/blob/{branchname}/{file_url_part}"
                title = thepath
                if lineend is not None:
                    title += f" lines {linestart}-{lineend}"

                elif linestart is not None:
                    title += f" line {linestart}"

                output[repo].append((title, url))

    if not output:
        return False

    embed = Embed()

    for repo, hits in output.items():
        value = ""
        count = 0
        for title, url in hits:
            count += 1
            entry = f"[`{title}`]({url})\n"
            if len(value) > 800:
                if not count:
                    value = f"Good job even a single entry is too long to fit within Discord's embed field limits. There were {len(hits)}."
                    break

                value += f"...and {len(hits)-count} more."
                break

            value += entry

        embed.add_field(name=repo, value=value)

    await channel.send(embed=embed)

    return True


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


async def get_github_object(url: str, *, params=None) -> Any:
    #logger.debug(f"Fetching github object at URL {url}...")

    session = master.get_cache(GITHUB_SESSION)
    cache = master.get_cache(GITHUB_CACHE)

    response = None
    paramstr = str(params)

    if (url, paramstr) in cache:
        contents, date = cache[(url, paramstr)]
        response = await session.get(url, headers={"If-Modified-Since": date}, params=params)
        if response.status == 304:
            return contents

    else:
        response = await session.get(url, params=params)

    if response.status != 200:
        txt = await response.text()
        raise Exception(f"GitHub API call returned non-200 code: {txt}")

    contents = await response.json()
    if "Last-Modified" in response.headers:
        cache[(url, paramstr)] = contents, response.headers["Last-Modified"]

    return contents
