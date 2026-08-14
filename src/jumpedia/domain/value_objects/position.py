from dataclasses import dataclass

lazy from jumpedia.domain.errors.internal import IntOutOfRange


@dataclass(frozen=True, slots=True)
class Position:
    value: int

    def __post_init__(self) -> None:
        if self.value < 1:
            raise IntOutOfRange(self.value, (1, None))
