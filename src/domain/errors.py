import typing as t
from string.templatelib import Template

from domain.entities.member import MemberEntity
from domain.entities.task import TaskEntity
from domain.enums.rank import AnyRankT
from domain.types.collection_entry import CollectionT
from domain.value_objects.attribute import AttributeSlot
from domain.value_objects.field_slot import FieldSlotStr

if t.TYPE_CHECKING:
    from domain.entities.base import BaseEntity
    from domain.entities.community import CommunityEntity
    from domain.value_objects.string import Str


# --- Base ---
class DomainError(Exception):
    def __init__(self) -> None:
        if type(self) is DomainError:
            raise RuntimeError("Instance of base exception class created")

        super().__init__()


# --- Invalid String ---
class EmptyString(DomainError):
    pass


class DoubleBacktick(DomainError):
    pass


# --- Context ---
class NotInServer(DomainError):
    pass


class NotInCommunity(DomainError):
    pass


class InCommunity(DomainError):
    def __init__(self, community: CommunityEntity) -> None:
        super().__init__()
        self.community = community


# --- Permission ---
class NotAllowed(DomainError):
    def __init__(self, rank: AnyRankT, required: AnyRankT) -> None:
        super().__init__()
        self.rank = rank
        self.required = required


class NotFoundByName(DomainError):
    def __init__(self, name: Str, type: type[BaseEntity]) -> None:
        super().__init__()
        self.name = name
        self.type = type


class NotFoundBySyn(DomainError):
    def __init__(self, syn: Str, type: type[BaseEntity]) -> None:
        super().__init__()
        self.syn = syn
        self.type = type


class NameTooLong(DomainError):
    def __init__(self, name: Str, limit: int, type: type[BaseEntity]) -> None:
        super().__init__()
        self.name = name
        self.limit = limit
        self.type = type


class SynAlreadyTaken(DomainError):
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


class NameNotDifferent(DomainError):
    def __init__(self, name: Str) -> None:
        super().__init__()
        self.name = name


class AliasesNotDifferent(DomainError):
    def __init__(self, aliases: tuple[Str, ...]) -> None:
        super().__init__()
        self.aliases = aliases

class CollectionNotDifferent(DomainError):
    def __init__(self, collection: CollectionT) -> None:
        super().__init__()
        self.collection = collection

class ServerAlreadyConnectedToACommunity(DomainError):
    def __init__(self, server_id: int, community: CommunityEntity) -> None:
        super().__init__()
        self.server_id = server_id
        self.community = community


class CountLimitReached(DomainError):
    def __init__(self, limit: int, type: type[BaseEntity]) -> None:
        super().__init__()
        self.limit = limit
        self.type = type


class AliasCountLimitReached(DomainError):
    def __init__(self, limit: int, entity_name: Str, aliases: tuple[Str, ...]) -> None:
        super().__init__()
        self.limit = limit
        self.entity_name = entity_name
        self.aliases = aliases


class SlotCountDefinitionLimitExceeded(DomainError):
    def __init__(
        self, min: int, max: int, min_min: int, min_max: int, max_max: int | None
    ) -> None:
        super().__init__()

        self.min = min
        self.max = max
        self.min_min = min_min
        self.min_max = min_max
        self.max_max = max_max


class InitialSlotCountMustBeZero(DomainError):
    pass


class DuplicateUniqueRequiredString(DomainError):
    def __init__(self, first: Str, second: Str) -> None:
        super().__init__()
        self.first = first
        self.second = second


class NoDefaultSelectedList(DomainError):
    def __init__(self) -> None:
        pass


class MemberDoesNotHaveTask(DomainError):
    def __init__(self, member: MemberEntity) -> None:
        super().__init__()
        self.member = member


class MemberAlreadyHasTask(DomainError):
    def __init__(self, member: MemberEntity, task: TaskEntity) -> None:
        super().__init__()
        self.member = member
        self.task = task


class TasksDoNotMatchMinOrMaxSlotCountCriteria(DomainError):
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


# --- Internal Errors --- #


class InternalError(Exception):
    pass


class NotFoundById(InternalError):
    def __init__(self, type: type[BaseEntity]) -> None:
        super().__init__()
        self.type = type
