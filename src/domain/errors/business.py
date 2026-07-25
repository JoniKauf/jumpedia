"""Expected business errors that should be handled gracefully."""

import typing as t
from dataclasses import dataclass

lazy from domain.entities.member import MemberEntity
lazy from domain.entities.task import TaskEntity
lazy from domain.enums.rank import AnyRankT
lazy from domain.typing.collection_entry import AbstractCollectionT
lazy from domain.value_objects.field_slot import FieldSlotStr
lazy from domain.entities.base import BaseEntity
lazy from domain.entities.community import CommunityEntity
lazy from domain.value_objects.string import Str


# --- Base --- #
@dataclass()
class BusinessError(Exception):
    pass


# --- Invalid String --- #
@dataclass()
class EmptyString(BusinessError):
    pass


@dataclass()
class DoubleBacktick(BusinessError):
    pass


# --- Access --- #
@dataclass()
class NotInServer(BusinessError):
    pass


@dataclass()
class NotInCommunity(BusinessError):
    pass


@dataclass()
class InCommunity(BusinessError):
    community: CommunityEntity


@dataclass()
class NoDefaultSelectedList(BusinessError):
    community: CommunityEntity


# --- Permission --- #
@dataclass()
class NotAllowed(BusinessError):
    rank: AnyRankT
    required: AnyRankT


# --- Not Found --- #
@dataclass()
class NotFoundByName(BusinessError):
    type: type[BaseEntity]
    name: Str


@dataclass()
class NotFoundBySyn(BusinessError):
    type: type[BaseEntity]
    syn: Str


# --- Invalid Input --- #
@dataclass()
class NameTooLong(BusinessError):
    type: type[BaseEntity]
    name: Str
    limit: int


# --- No Difference --- #
@dataclass()
class NameNotDifferent(BusinessError):
    entity: BaseEntity


@dataclass()
class AliasesDidNotChange(BusinessError):
    type: type[BaseEntity]
    aliases: tuple[Str, ...]


@dataclass()
class CollectionDidNotChange(BusinessError):
    collection: AbstractCollectionT


# --- Slot Count Configuration --- #
@dataclass()
class SlotCountConfigLimitExceeded(BusinessError):
    min: int
    max: int
    min_min: int
    min_max: int
    max_max: int | None


@dataclass()
class InitialSlotCountMustBeZero(BusinessError):
    pass


# --- Task --- #
@dataclass()
class TasksDoNotMatchMinOrMaxSlotCountCriteria(BusinessError):
    min_slot_count: int
    max_slot_count: int
    invalid: t.Mapping[TaskEntity, tuple[FieldSlotStr, ...]]


# --- Member Task --- #
@dataclass()
class MemberDoesNotHaveTask(BusinessError):
    member: MemberEntity


@dataclass()
class MemberAlreadyHasTask(BusinessError):
    member: MemberEntity
    task: TaskEntity


# --- Count Limit Reached --- #
@dataclass()
class CountLimitReached(BusinessError):
    limit: int
    type: type[BaseEntity]


@dataclass()
class AliasCountLimitSurpassed(BusinessError):
    limit: int
    entity_name: Str
    aliases: t.Sequence[Str]


# --- Server --- #
@dataclass()
class ServerAlreadyConnectedToACommunity(BusinessError):
    server_id: int
    community: CommunityEntity


# --- Misc --- #
@dataclass()
class SynAlreadyTaken(BusinessError):
    current: BaseEntity
    new: Str
    alias_of_current_collides: bool
    alias_of_new_collides: bool


@dataclass()
class SynsNotUnique(BusinessError):
    type: type[BaseEntity]
    collision: Str


@dataclass()
class NotUniqueSynsAcrossNamesAndAliases(BusinessError):
    type: type[BaseEntity]
    first_name: Str
    second_name: Str
    first_colliding_alias: Str | None
    second_colliding_alias: Str | None
