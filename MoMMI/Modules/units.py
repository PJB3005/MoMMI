import asyncio
import operator
import re
from decimal import Decimal
from functools import reduce
from typing import Match, Optional, List, Pattern
import unit_converter
from unit_converter.converter import converts
from unit_converter.parser import UnitParser
from unit_converter.data import UNITS, PREFIXES
from unit_converter.units import Unit
from discord import Message
from MoMMI import command, MChannel


async def load(loop: asyncio.AbstractEventLoop) -> None:
    unit_type = unit_converter.units.Unit
    tempunits = list(UNITS.values())
    for unit in tempunits:
        if unit.name not in UNITS:
            UNITS[unit.name] = unit

        if unit.symbol not in UNITS:
            UNITS[unit.symbol] = unit

    UNITS["mph"] = unit_type("mph", "mph", L=1, T=-1, coef=Decimal("0.44704"))
    UNITS["Wh"] = unit_type("Wh", "watt-hours", M=1, L=2, T=-2, coef=Decimal("3600"))


@command("unit", r"(?:unit)?\s*`?(.+?)`?\s+(?:as|to)\s+`?(.+?)`?$")
async def unit_command(channel: MChannel, match: Match, message: Message) -> None:
    fromunit = match.group(1).strip()
    tounit = match.group(2).strip()

    try:
        result = converts(fromunit, tounit)
        await channel.send(result + " " + tounit)

    except unit_converter.exceptions.UnConsistentUnitsError as e:
        await channel.send(e.value.replace("*", "\\*"))

    except unit_converter.exceptions.UnitDoesntExistError as e:
        await channel.send(e.value.replace("*", "\\*"))

    except ParserError as e:
        await channel.send(f"Parser error: {e.value}")

class UnitParserMoMMI(unit_converter.parser.UnitParser):
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

            if unit is None:
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


class ParserError(ValueError):
    def __init__(self, problem: str) -> None:
        super().__init__()
        self.value = problem

    def __str__(self) -> str:
        return f"ParserError({repr(self.value)})"


class Parser:
    def __init__(self, string: str, startpos: int = 0) -> None:
        self.string = string
        self.position = startpos

    @property
    def eof(self) -> bool:
        return self.position >= len(self.string)

    def take(self) -> Optional[str]:
        if self.eof:
            return None

        ret = self.string[self.position]
        self.position += 1
        return ret

    def peek(self) -> Optional[str]:
        if self.eof:
            return None

        return self.string[self.position]

    def skip(self, amount: int = 1) -> None:
        self.position = min(len(self.string), amount + self.position)

    def take_re(self, pattern: Pattern[str]) -> Optional[str]:
        if self.eof:
            return None

        match = pattern.match(self.string, self.position)
        if not match:
            return ""

        assert match.start() == self.position
        self.position = match.end()
        return match[0]

