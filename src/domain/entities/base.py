import typing as t


class BaseEntity[*Ts]:
    def __init__(self, *composite_key: *Ts) -> None:
        self._composite_key = composite_key

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._composite_key == other._composite_key

    def __hash__(self) -> int:
        return hash(self._composite_key)
