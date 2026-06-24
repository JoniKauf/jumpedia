import typing as t
from string.templatelib import Template

from domain.enums.rank import AnyRankT
from domain.value_objects.attribute import AttributeSlot

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


class NameTooLong(DomainError):
    def __init__(self, name: Str, limit: int, type: type[BaseEntity]) -> None:
        super().__init__()
        self.name = name
        self.limit = limit
        self.type = type


class NameAlreadyTaken(DomainError):
    def __init__(self, name: Str, existing: BaseEntity) -> None:
        super().__init__()
        self.name = name
        self.existing = existing


class SynAlreadyTaken(DomainError):
    def __init__(self, existing: BaseEntity) -> None:
        super().__init__()
        self.existing = existing


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
    def __init__(self, limit: int, entity_name: Str) -> None:
        super().__init__()
        self.limit = limit
        self.entity_name = entity_name


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



class InternalError(Exception):
    pass


class NotFoundById(InternalError):
    def __init__(self, type: type[BaseEntity]) -> None:
        super().__init__()
        self.type = type