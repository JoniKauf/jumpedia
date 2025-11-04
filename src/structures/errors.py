from dataclasses import dataclass
import typing as t

from src.structures.attribute import SlotStr
from src.utils import text
from src.utils.text import RealStr
from src.utils.types import SetLike

if t.TYPE_CHECKING:
    from . import BaseStructure
    from .attribute.slot_str import SlotTypeT
    from .community import Community
    from .attribute import BaseAttribute
    from .attribute.collection import Collection


@t.dataclass_transform(eq_default=False)
class _BaseStructureErrorMeta(type):
    def __new__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, t.Any],
        **kwds: t.Any,
    ):
        cls = super().__new__(cls, name, bases, namespace, **kwds)
        return dataclass(eq=False)(cls)


class BaseStructureError(Exception, metaclass=_BaseStructureErrorMeta):
    def __init_subclass__(cls) -> None:
        if cls is BaseStructureError:
            raise RuntimeError
        super().__init_subclass__()


class StructureNotFoundError(BaseStructureError):
    structure_type: type[BaseStructure]


class StructureFoundError(BaseStructureError):
    structure: BaseStructure


class SynAlreadyTakenError(BaseStructureError):
    syn: str
    structure: BaseStructure


class ServerAlreadyConnectedToCommunityError(BaseStructureError):
    server_id: int
    structure: Community


class ServerNotConnectedToACommunityError(BaseStructureError):
    server_id: int


class LimitReachedError(BaseStructureError):
    limit: int
    type: type


class CollectionEntryNotFoundError(BaseStructureError):
    real_slot: RealStr
    collection: Collection


class CollectionEntryDuplicateError(BaseStructureError):
    duplicate: SlotStr


class TooManyAliasesError(BaseStructureError):
    aliases: SetLike[text.NormStr]
    limit: int
    structure_type: type[BaseStructure]

class TooLongSynError(BaseStructureError):
    syn: str
    limit: int
    structure_type: type[BaseStructure]

class ElementCountOutOfRangeError(BaseStructureError):
    min: int
    max: int
    structure_type: type[BaseStructure]


class InvalidSlotStrError(BaseStructureError):
    s: str
    expected_type: type[SlotTypeT]
