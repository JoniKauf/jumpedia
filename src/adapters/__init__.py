from dataclasses import dataclass
from typing import Any, dataclass_transform


@dataclass_transform(frozen_default=True)
class _AdapterMeta(type):
    def __new__(
        mcls: type[_AdapterMeta],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        /,
        **kwargs: Any,
    ) -> _AdapterMeta:
        cls = super().__new__(mcls, name, bases, namespace, **kwargs)
        return dataclass(frozen=True)(cls)  # type: ignore


class BaseAdapter(metaclass=_AdapterMeta):
    def __post_init__(self) -> None:
        if self.__class__ is BaseAdapter:
            raise TypeError
