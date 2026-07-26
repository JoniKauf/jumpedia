"""Expected business errors that should be handled gracefully."""

import typing as t
from dataclasses import dataclass

from domain.entities.attribute import AttributeEntity
lazy from domain.entities.member import MemberEntity
lazy from domain.entities.task import TaskEntity
from domain.enums.attribute import AttributeSlotType
from domain.enums.concept import Concept
lazy from domain.enums.rank import AnyRankT
lazy from domain.typing.collection_entry import AbstractCollectionT, FrozenCollectionT
from domain.typing.entity import NamedEntityT
lazy from domain.value_objects.field_slot import FieldSlotStr
lazy from domain.entities.base import BaseEntity
lazy from domain.entities.community import CommunityEntity
lazy from domain.value_objects.string import Str

type AnyBusinessErrorT = (
    EmptyString
    | DoubleBacktick
    | NotInServer
    | NotInCommunity
    | ServerAlreadyLinked
    | NoDefaultSelectedList
    | NotAllowed
    | NotFoundByName
    | NotFoundBySyn
    | StrTooLong
    | NewNameEqualToCurrent
    | AliasesDidNotChange
    | CollectionDidNotChange
    | SlotCountConfigLimitExceeded
    | TasksDoNotMatchMinOrMaxSlotCountCriteria
    | MemberDoesNotHaveTask
    | MemberAlreadyHasTask
    | CountLimitReached
    | AliasCountLimitSurpassed
    | ServerAlreadyConnectedToACommunity
    | SynAlreadyTaken
    | AliasesNotUnique
    | SynsNotUnique
    | NotUniqueValuesAndAliasesAcrossCollection
    | CommunityLimitOutOfRange
    | ApiUnreachable
    | NotDoableForKindedAttribute
    | AttributeMentionedMoreThanOnce
    | AttributeNotMentioned
    | NewCollectionUnfittingForExistingFieldSlots
    | FieldMappingAttributesNotUnique
    | SlotCountConfigNotFulfilled
    | CollectionEntryNotFoundViaSyn
    | NotUniqueSlots
    | CannotChangeOwnRank
    | CannotChangeRankOfUserWithEqualOrHigherPower
    | CannotChangeToRankOfEqualOrHigherPower
    | UserAlreadyHasRank
    | InvalidSlotForSlotType
)

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
class ServerAlreadyLinked(BusinessError):
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
    concept: Concept
    name: Str


@dataclass()
class NotFoundBySyn(BusinessError):
    concept: Concept
    syn: Str


# --- Invalid Input --- #
@dataclass()
class StrTooLong(BusinessError):
    concept: Concept
    s: Str
    limit: int


# --- No Difference --- #
@dataclass()
class NewNameEqualToCurrent(BusinessError):
    entity: NamedEntityT


@dataclass()
class AliasesDidNotChange(BusinessError):
    entity: NamedEntityT
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


# --- Task --- #
@dataclass()
class TasksDoNotMatchMinOrMaxSlotCountCriteria(BusinessError):
    attribute: AttributeEntity
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
    concept: Concept
    limit: int


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
    current: NamedEntityT
    new: Str
    alias_of_current_collides: bool
    alias_of_new_collides: bool


@dataclass()
class AliasesNotUnique(BusinessError):
    concept: Concept
    collision: Str


@dataclass()
class SynsNotUnique(BusinessError):
    concept: Concept
    collision: Str


@dataclass()
class NotUniqueValuesAndAliasesAcrossCollection(BusinessError):
    first_value: FieldSlotStr
    second_value: FieldSlotStr
    first_colliding_alias: FieldSlotStr | None
    second_colliding_alias: FieldSlotStr | None


@dataclass()
class CommunityLimitOutOfRange(BusinessError):
    name: Str
    limit: int
    min: int
    max: int


@dataclass()
class ApiUnreachable(BusinessError):
    api: Str


@dataclass()
class NotDoableForKindedAttribute(BusinessError):
    attribute: AttributeEntity


@dataclass()
class AttributeMentionedMoreThanOnce(BusinessError):
    attribute: AttributeEntity


@dataclass()
class AttributeNotMentioned(BusinessError):
    attribute: AttributeEntity


@dataclass()
class NewCollectionUnfittingForExistingFieldSlots(BusinessError):
    attribute: AttributeEntity
    new_collection: FrozenCollectionT
    task_to_invalid_slots: frozendict[TaskEntity, tuple[FieldSlotStr, ...]]


@dataclass()
class FieldMappingAttributesNotUnique(BusinessError):
    collision: AttributeEntity


@dataclass()
class SlotCountConfigNotFulfilled(BusinessError):
    attribute: AttributeEntity
    field: tuple[FieldSlotStr, ...]


@dataclass()
class CollectionEntryNotFoundViaSyn(BusinessError):
    attribute: AttributeEntity
    collection: FrozenCollectionT
    syn: FieldSlotStr


@dataclass()
class NotUniqueSlots(BusinessError):
    attribute: AttributeEntity
    field: tuple[FieldSlotStr, ...]


@dataclass()
class CannotChangeOwnRank(BusinessError):
    pass


@dataclass()
class CannotChangeRankOfUserWithEqualOrHigherPower(BusinessError):
    actor_rank: AnyRankT
    target_rank: AnyRankT


@dataclass()
class CannotChangeToRankOfEqualOrHigherPower(BusinessError):
    actor_rank: AnyRankT
    target_rank: AnyRankT


@dataclass()
class UserAlreadyHasRank(BusinessError):
    user_concept: t.Literal[Concept.USER, Concept.MEMBER]


@dataclass()
class InvalidSlotForSlotType(BusinessError):
    slot_type: AttributeSlotType
    slot: FieldSlotStr
