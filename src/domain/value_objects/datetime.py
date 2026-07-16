import datetime as dt
from dataclasses import dataclass
import typing as t

@dataclass(frozen=True, slots=True)
class DateTime:
    value: dt.datetime

    def __str__(self) -> str:
        return self.value.strftime(DateTime.FORMAT)

    FORMAT: t.ClassVar[t.Final[str]] = "%A, %Y/%m/%d %H:%M:%S (UTC)"

    @classmethod
    def now(cls) -> t.Self:
        return cls(dt.datetime.now(dt.UTC))

    @classmethod
    def parse(cls, s: str) -> t.Self:
        return cls(dt.datetime.strptime(s, cls.FORMAT).replace(tzinfo=dt.UTC))
    