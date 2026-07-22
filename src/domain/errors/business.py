import typing as t
from string.templatelib import Template

from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.enums.rank import AnyRankT
from domain.typing.collection_entry import AbstractCollectionT
from domain.value_objects.attribute import AttributeFieldConfig
from domain.value_objects.field_slot import FieldSlotStr

if t.TYPE_CHECKING:
    from domain.entities.base import BaseEntity
    from domain.entities.community import CommunityEntity
    from domain.value_objects.string import Str


# --- Base ---
class BusinessError(Exception):
    pass


# --- Invalid String ---
class EmptyString(BusinessError):
    pass


class DoubleBacktick(BusinessError):
    pass


# --- Context ---
class NotInServer(BusinessError):
    pass


class NotInCommunity(BusinessError):
    pass


class InCommunity(BusinessError):
    def __init__(self, community: CommunityEntity) -> None:
        super().__init__()
        self.community = community


# --- Permission ---
class NotAllowed(BusinessError):
    def __init__(self, rank: AnyRankT, required: AnyRankT) -> None:
        super().__init__()
        self.rank = rank
        self.required = required


class NotFoundByName(BusinessError):
    def __init__(self, name: Str, type: type[BaseEntity]) -> None:
        super().__init__()
        self.name = name
        self.type = type


class NotFoundBySyn(BusinessError):
    def __init__(self, syn: Str, type: type[BaseEntity]) -> None:
        super().__init__()
        self.syn = syn
        self.type = type


class NameTooLong(BusinessError):
    def __init__(self, name: Str, limit: int, type: type[BaseEntity]) -> None:
        super().__init__()
        self.name = name
        self.limit = limit
        self.type = type


class SynAlreadyTaken(BusinessError):
    def __init__(
        self,
        existing: BaseEntity,
        new: Str,
        existing_is_alias: bool,
        new_is_alias: bool,
    ) -> None:
        super().__init__()
        self.existing = existing
        self.new = new
        self.existing_is_alias = existing_is_alias
        self.new_is_alias = new_is_alias


class NameNotDifferent(BusinessError):
    def __init__(self, name: Str, type: type[BaseEntity]) -> None:
        super().__init__()
        self.name = name
        self.type = type


class AliasesNotDifferent(BusinessError):
    def __init__(self, aliases: tuple[Str, ...]) -> None:
        super().__init__()
        self.aliases = aliases


class CollectionNotDifferent(BusinessError):
    def __init__(self, collection: AbstractCollectionT) -> None:
        super().__init__()
        self.collection = collection


class ServerAlreadyConnectedToACommunity(BusinessError):
    def __init__(self, server_id: int, community: CommunityEntity) -> None:
        super().__init__()
        self.server_id = server_id
        self.community = community


class CountLimitReached(BusinessError):
    def __init__(self, limit: int, type: type[BaseEntity]) -> None:
        super().__init__()
        self.limit = limit
        self.type = type


class AliasCountLimitReached(BusinessError):
    def __init__(self, limit: int, entity_name: Str, aliases: t.Sequence[Str]) -> None:
        super().__init__()
        self.limit = limit
        self.entity_name = entity_name
        self.aliases = aliases


class SlotCountDefinitionLimitExceeded(BusinessError):
    def __init__(
        self, min: int, max: int, min_min: int, min_max: int, max_max: int | None
    ) -> None:
        super().__init__()

        self.min = min
        self.max = max
        self.min_min = min_min
        self.min_max = min_max
        self.max_max = max_max


class InitialSlotCountMustBeZero(BusinessError):
    pass


class DuplicateUniqueRequiredString(BusinessError):
    def __init__(self, first: Str, second: Str) -> None:
        super().__init__()
        self.first = first
        self.second = second


class NoDefaultSelectedList(BusinessError):
    def __init__(self) -> None:
        pass


class MemberDoesNotHaveTask(BusinessError):
    def __init__(self, member: MemberEntity) -> None:
        super().__init__()
        self.member = member


class MemberAlreadyHasTask(BusinessError):
    def __init__(self, member: MemberEntity, task: TaskEntity) -> None:
        super().__init__()
        self.member = member
        self.task = task


class TasksDoNotMatchMinOrMaxSlotCountCriteria(BusinessError):
    def __init__(
        self,
        min_slot_count: int,
        max_slot_count: int,
        invalid: dict[TaskEntity, tuple[FieldSlotStr, ...]],
    ) -> None:
        super().__init__()
        self.min_slot_count = min_slot_count
        self.max_slot_count = max_slot_count
        self.invalid = invalid
