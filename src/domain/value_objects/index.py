from dataclasses import dataclass

from domain.errors.internal import IntOutOfRange


@dataclass(frozen=True, slots=True)
class Index:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise IntOutOfRange(self.value, (0, None))
