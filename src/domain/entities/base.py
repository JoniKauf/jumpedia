import typing as t
from dataclasses import dataclass, field


@dataclass(init=False, frozen=True, slots=True)
class BaseEntity[*Ts]:
    key: tuple[*Ts]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False

        return self.key == other.key

    def __hash__(self) -> int:
        return hash(self.key)

    def __repr__(self) -> str:
        s = type(self).__qualname__ + "("

        s += ", ".join(
            f"{k!r}={v!r}"
            for k, v in vars(self).items()
            if k.startswith("_") and not k.startswith("__")
        )

        return s + ")"

    def __str__(self) -> str:
        return self.__repr__()
