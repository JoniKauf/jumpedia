import typing as t

if t.TYPE_CHECKING:
    from src.structures import BaseStructure
    from src.structures.community import Community
    from src.structures.attribute.slot_type import SlotTypeT


class BaseStructureError(Exception):
    def __init_subclass__(cls) -> None:
        if cls is BaseStructureError:
            raise RuntimeError
        super().__init_subclass__()


class StructureNotFoundError(BaseStructureError):
    pass


class StructureFoundError(BaseStructureError):
    def __init__(self, structure: BaseStructure, *args: object) -> None:
        self.structure = structure
        super().__init__(*args)


class SynAlreadyTakenError[T: BaseStructure](BaseStructureError):
    def __init__(self, syn: str, structure: T, *args: object) -> None:
        self.syn = syn
        self.structure = structure
        super().__init__(*args)


class ServerAlreadyConnectedToCommunityError(BaseStructureError):
    def __init__(self, server_id: int, structure: Community, *args: object) -> None:
        self.server_id = server_id
        self.structure = structure
        super().__init__(*args)


class ServerNotConnectedToACommunityError(BaseStructureError):
    def __init__(self, server_id: int, *args: object) -> None:
        self.server_id = server_id
        super().__init__(*args)


class LimitOfStructuresReachedError(BaseStructureError):
    def __init__(self, limit: int, *args: object) -> None:
        self.limit = limit
        super().__init__(*args)


class SynTooLongError(BaseStructureError):
    def __init__(
        self,
        length: int,
        limit: int,
        structure_type: type[BaseStructure],
        *args: object,
    ) -> None:
        self.length = length
        self.limit = limit
        self.structure_type = structure_type
        super().__init__(*args)


class ElementCountOutOfRangeError(BaseStructureError):
    def __init__(self, min: int, max: int, structure_type: type, *args: object) -> None:
        self.min = min
        self.max = max
        self.structure_type = structure_type
        super().__init__(*args)

class InvalidSlotStr(BaseStructureError):
    def __init__(self, s: str, expected_type: type[SlotTypeT], *args: object) -> None:
        self.s = s
        self.expected_type = expected_type
        super().__init__(*args)