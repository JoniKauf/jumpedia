import typing as t
from . import BaseStructure
from .community import Community


class BaseStructureError[T: BaseStructure](Exception):
    def __init_subclass__(cls) -> None:
        if cls is BaseStructureError:
            raise RuntimeError
        super().__init_subclass__()

    def __init__(self, structure_type: type[T], *args: object) -> None:
        self.structure_type = structure_type
        super().__init__(*args)


class StructureNotFoundError[T: BaseStructure](
    BaseStructureError[T], LookupError
): pass

class StructureFoundError[T: BaseStructure](
    BaseStructureError[T], LookupError
):
    def __init__(self, structure: T, *args: object) -> None:
        self.structure = structure
        super().__init__(type(structure), *args)


class SynAlreadyTakenError[T: BaseStructure](StructureFoundError[T]):
    def __init__(self, syn: str, structure: T, *args: object) -> None:
        self.syn = syn
        super().__init__(structure, *args)


class ServerAlreadyConnectedToCommunityError(StructureFoundError[Community]):
    pass

class LimitOfStructuresReachedError(BaseStructureError):
    def __init__(self, limit: int, structure_type: type[BaseStructure], *args: object) -> None:
        self.limit = limit
        super().__init__(structure_type, *args)

class SynTooLongError(BaseStructureError):
    def __init__(self, length: int, limit: int, structure_type: type[BaseStructure], *args: object) -> None:
        self.length = length
        self.limit = limit
        super().__init__(structure_type, *args)


class ElementCountOutOfRangeError(BaseStructureError):
    def __init__(self, min: int, max: int, structure_type: type, *args: object) -> None:
        self.min = min
        self.max = max
        super().__init__(structure_type, *args)

def __verify_integrity() -> None:
    for obj in __dict__.values():
        if (
            isinstance(obj, type)
            and isinstance(obj, Exception)
            and not isinstance(obj, BaseStructureError)
        ):
            raise RuntimeError

__verify_integrity()
