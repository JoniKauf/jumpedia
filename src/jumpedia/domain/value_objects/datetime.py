import datetime as dt
import typing as t
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DateTimeWrapper:
    value: dt.datetime

    def __str__(self) -> str:
        return self.value.strftime(DateTimeWrapper.FORMAT)

    FORMAT: t.ClassVar[t.Final[str]] = "%Y/%m/%d %H:%M:%S (UTC)"

    @classmethod
    def now(cls) -> t.Self:
        return cls(dt.datetime.now(dt.UTC))

    @classmethod
    def parse(cls, s: str) -> t.Self:
        return cls(dt.datetime.strptime(s, cls.FORMAT).replace(tzinfo=dt.UTC))
