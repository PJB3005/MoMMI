import asyncio
import tempfile
import aiohttp
import os
from datetime import date, timedelta
from logging import getLogger
from subprocess import PIPE
from typing import Match, Union, Tuple, List
from discord import Message
from MoMMI import command, MChannel, add_reaction, remove_reaction, master

LOGGER = getLogger(__name__)


def sizeof_fmt(num: Union[float, int]) -> str:
    for unit in ["","Ki","Mi","Gi","Ti","Pi","Ei","Zi"]:
        if abs(num) < 1024:
            return f"{num:.1f}{unit}B"
        num /= 1024
    return f"{num:.1f}YiB"


# Returns (stdout to lines_returned lines, runtime log size)
async def get_runtimes(file_date: date, lines_returned: int, condenser_path: str, base_url: str) -> Tuple[str, int]:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8") as input_file:
        LOGGER.debug(f"Grabbing file with date: {file_date.isoformat()}")
        url = f"{base_url}{file_date.isoformat()}-runtime.log"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                input_file.write(await response.text())

        condenser = await asyncio.create_subprocess_exec(condenser_path, "--input", input_file.name, stdout=PIPE)
        stdout, stderr = await condenser.communicate()
        stdout = stdout.decode("UTF-8").split("\n")
        size = os.path.getsize(input_file.name)

        lines = []
        for i in range(lines_returned):
            lines.append(stdout[i])

        return ("\n".join(lines), size)


@command("runtimelog", r"runtimelog(?:\s+(.*))?")
async def runtimelog_command(channel: MChannel, match: Match, message: Message) -> None:
    try:
        runtime_condenser = channel.module_config("runtimelog.runtime-condenser")
        base_url = channel.server_config("modules.runtimelog.base-url")

    except ValueError:
        return

    file_date = date.today()
    arg_group = match.group(1)
    if arg_group:
        args = arg_group.split(" ")
        if args:
            if args[0].startswith("yesterday"):
                file_date = file_date - timedelta(days=1)
            elif len(args) == 3: # specific date
                try:
                    year = int(args[0])
                    month = int(args[1])
                    day = int(args[2])
                    file_date = date(year, month, day)

                except TypeError:
                    await channel.send("Invalid date format. Format is `year month day`.")
                    return
            else:
                await channel.send("Invalid date format. Format is `year month day`.")
                return

    asyncio.ensure_future(add_reaction(message, "🕒"))
    try:
        msg, size = await get_runtimes(file_date, 12, runtime_condenser, base_url)
        await channel.send(f"```\n{msg}```\nTotal runtime log file size: {sizeof_fmt(size)}")
    except:
        LOGGER.exception("runtimelog exception")
        await channel.send("Something went wrong. You're not trying to do time travel, are you?")

    #await master.client.remove_reaction(message, "🕒", channel.server.get_server().me)
