from typing import Pattern, Optional

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
