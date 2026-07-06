from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Span:
    begin: int
    end: int
