from typing import ClassVar, Self


class Person:
    LOOKUP: ClassVar[dict[str | int, 'Person"']]

    def __init__(self, value: str, *, id: int) -> None:
        self.value: str = value
        self.id: int = id
        self._add()
    
    def _add(self):
        self.__class__.LOOKUP[self.value] = self
        self.__class__.LOOKUP[self.id] = self


