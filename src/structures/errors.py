import typing as t
from dataclasses import dataclass

from utils import text

if t.TYPE_CHECKING:
    from . import BaseStructure
    from .attribute import BaseAttribute, SlotStr
    from .attribute.collection import Collection
    from .attribute.slot_str import SlotTypeT
    from .community import Community


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


class SynsAlreadyTakenError(BaseStructureError):
    structures: frozenset[BaseStructure]


class ServerAlreadyConnectedToCommunityError(BaseStructureError):
    server_id: int
    structure: Community


class ServerNotConnectedToACommunityError(BaseStructureError):
    server_id: int


class LimitReachedError(BaseStructureError):
    limit: int
    type: type


class CollectionEntryNotFoundError(BaseStructureError):
    real_slot: text.RealStr
    collection: Collection


class CollectionEntryDuplicateError(BaseStructureError):
    duplicate: SlotStr


class TooLongSynError(BaseStructureError):
    syn: str
    limit: int
    structure_type: type[BaseStructure]


class TooManyAliasesError(BaseStructureError):
    aliases: frozenset[text.NormStr]
    limit: int
    structure_type: type[BaseStructure]


class AttributeValueSlotCountOutOfRangeError(BaseStructureError):
    value: tuple[text.RealStr, ...]
    min: int
    max: int
    attribute: BaseAttribute


class AttributeMinSlotsOrMaxSlotsOutOfRangeError(BaseStructureError):
    min: int
    max: int
    min_min: int
    max_max: int


class InvalidSlotStrError(BaseStructureError):
    s: str
    expected_type: type[SlotTypeT]


class CommunityUserAlreadyHasTaskError(BaseStructureError):
    task_id: int
    community_user_id: int


class CommunityUserDoesNotHaveTaskError(BaseStructureError):
    task_id: int
    community_user_id: int


class EmptyStringError(BaseStructureError):
    pass


class NotUniqueStringError(BaseStructureError):
    given: text.RealStr
    existing: text.RealStr
