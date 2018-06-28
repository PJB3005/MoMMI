import asyncio
import operator
import re
from decimal import Decimal
from functools import reduce
from typing import Match, Optional, List, Pattern
import unit_converter
from unit_converter.converter import convert
from unit_converter.parser import UnitParser, QuantityParser
from unit_converter.data import UNITS, PREFIXES
from unit_converter.units import Unit
from discord import Message
from MoMMI import command, MChannel
from MoMMI.Modules.parser import Parser, ParserError


async def load(loop: asyncio.AbstractEventLoop) -> None:
    UNITS["mph"] = Unit("mph", "mph", L=1, T=-1, coef=Decimal("0.44704"))
    UNITS["Wh"] = Unit("Wh", "watt-hours", M=1, L=2, T=-2, coef=Decimal("3600"))
    UNITS["L"] = Unit("L", "litre", L=3, coef=Decimal("0.001"))
    UNITS["gal"] = Unit("gal", "gallon", L=3, coef=Decimal("0.00378541"))
    UNITS["lb"] = Unit("lb", "pound", M=1, coef=Decimal("0.45359237"))
    tempunits = list(UNITS.values())
    for unit in tempunits:
        if unit.name not in UNITS:
            UNITS[unit.name] = unit

        if unit.symbol not in UNITS:
            UNITS[unit.symbol] = unit

    QuantityParser.quantity_re = re.compile(r"(?P<value>-?\d+[.,]?\d*)? *(?P<unit>.*)")


@command("unit", r"(?:unit)?\s*`?(\d+\s+\S+?)`?\s+(?:as|to)\s+`?(\S+?)`?$")
async def unit_command(channel: MChannel, match: Match, message: Message) -> None:
    fromunit = match.group(1).strip()
    tounit = match.group(2).strip()

    try:
        result = convert(fromunit, tounit)
        await channel.send(f"{result} {tounit}")

    except unit_converter.exceptions.UnConsistentUnitsError as e:
        await channel.send(e.value.replace("*", "\\*"))

    except unit_converter.exceptions.UnitDoesntExistError as e:
        await channel.send(e.value.replace("*", "\\*"))

    except ParserError as e:
        await channel.send(f"Parser error: {e.value}")


class UnitParserMoMMI(UnitParser):
    word_re = re.compile(r"[a-zA-Z°Ωµ]*")
    number_re = re.compile(r"(-)?[0-9]+")

    def parse(self, input_unit: str) -> Unit:
        p = Parser(input_unit)
        units: List[Unit] = []
        exponent = 1.0
        while True:
            unit_s = p.take_re(self.word_re)
            if unit_s == "":
                raise ParserError(f"Expected unit, got {p.peek()}")

            if unit_s is None:
                raise ParserError(f"Expected unit, got EOF")

            unit: Unit

            # Figure out which unit.
            for prefix_s in PREFIXES.keys():
                if unit_s.startswith(prefix_s) and unit_s[len(prefix_s):] in UNITS:
                    unit = PREFIXES[prefix_s] * UNITS[unit_s[len(prefix_s):]]
                    break

            else:
                raise ParserError(f"Unknown unit '{unit_s}'")

            # Exponent
            if p.peek() == "^":
                p.skip()
                exponent_s = p.take_re(self.number_re)
                if exponent_s == "":
                    raise ParserError(f"Expected number for exponent, got {p.peek()}")

                if exponent_s is None:
                    raise ParserError(f"Expected number for exponent, got EOF")

                exponent *= float(exponent_s)

            unit **= exponent
            exponent = 1.0

            units.append(unit)

            connector_s = p.take()
            if connector_s is None:
                break

            if connector_s == "*":
                continue

            if connector_s == "/":
                exponent *= -1.0
                continue

            raise ParserError(f"Expected connector or EOF, got {connector_s}")

        return reduce(operator.mul, units)


unit_converter.parser.UnitParser = UnitParserMoMMI
