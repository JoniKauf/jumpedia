from string.templatelib import Template

from domain.enums.rank import AnyRankT
import typing as t

if t.TYPE_CHECKING:
    from domain.entities.base import BaseEntity
    from domain.entities.community import CommunityEntity
    from domain.value_objects.string import StrStore


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


class NotFound(DomainError):
    def __init__(self, type: type[BaseEntity]) -> None:
        super().__init__()
        self.type = type


class NameTooLong(DomainError):
    def __init__(self, name: StrStore, limit: int, type: type[BaseEntity]) -> None:
        super().__init__()
        self.name = name
        self.limit = limit
        self.type = type


class NameAlreadyTaken(DomainError):
    def __init__(self, name: StrStore, existing: BaseEntity) -> None:
        super().__init__()
        self.name = name
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


class DuplicateUniqueRequiredString(DomainError):
    def __init__(self, first: StrStore, second: StrStore) -> None:
        super().__init__()
        self.first = first
        self.second = second
