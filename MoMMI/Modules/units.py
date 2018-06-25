import asyncio
from typing import Match
import unit_converter
from discord import Message
from MoMMI import command, MChannel


async def load(loop: asyncio.AbstractEventLoop) -> None:
    units_list = unit_converter.data.UNITS
    unit_type = unit_converter.units.Unit
    tempunits = list(units_list.values())
    for unit in tempunits:
        if unit.name not in units_list:
            units_list[unit.name] = unit

        if unit.symbol not in units_list:
            units_list[unit.symbol] = unit

    units_list["mph"] = unit_type("mph", "mph", L=1, T=-1)


@command("unit", r"(?:unit)?\s*`?(.+?)`?\s+(?:as|to)\s+`?(.+?)`?$")
async def unit_command(channel: MChannel, match: Match, message: Message) -> None:
    fromunit = match.group(1).strip()
    tounit = match.group(2).strip()

    try:
        result = unit_converter.converter.converts(fromunit, tounit)
        await channel.send(result + " " + tounit)

    except unit_converter.exceptions.UnConsistentUnitsError as e:
        await channel.send(e.value.replace("*", "\\*"))

    except unit_converter.exceptions.UnitDoesntExistError as e:
        await channel.send(e.value)

