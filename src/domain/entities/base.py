import typing as t


class BaseEntity:
    _id: int

    def __init__(self, id: int) -> None:
        if type(self) is BaseEntity:
            raise TypeError

        if id < 0:
            raise RuntimeError("ID must be 0 (not persisted) or higher (persisted)")

        self._id = id

    @property
    def id(self) -> int:
        if not self.is_persisted():
            raise RuntimeError("Programming Error: entity is not persisted!")

        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return False
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self.id)

    def is_persisted(self) -> bool:
        return self._id > 0
