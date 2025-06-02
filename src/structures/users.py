from dataclasses import dataclass, field
import re

from typing import TYPE_CHECKING, Callable, ClassVar, Final, Self, TypedDict

from discordtools import feedbackerrors as fbe
import discord as dc

from structures.ranks import AnyRank, ServerRank, MetaRank, CommunityRank

if TYPE_CHECKING:
    from structures.list import List
    from structures.community import Community



_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')

type UserIdentifierT = int | str | MetaUser | CommunityUser | ServerUser | dc.User | dc.Member


def extract_id(identifier: UserIdentifierT) -> int:
    if isinstance(identifier, str | int):
        return _user_id_to_int(identifier)
    
    if isinstance(identifier, CommunityUser | ServerUser):
        return identifier.user.id

    if isinstance(identifier, MetaUser | dc.User | dc.Member):
        return identifier.id
    
    raise TypeError()

@staticmethod
def _user_id_to_int(user_id: str | int) -> int:
    if isinstance(user_id, int):
        if user_id < 0:
            raise fbe.InvalidUserFormat(user_id)
        
        return user_id
    
    if user_id.isdigit():
        id = int(user_id)
    elif match := re.match(_USER_MENTION_PATTERN, user_id.strip()):
        id = int(match.group(1) or match.group(2))
    else:
        raise fbe.InvalidUserFormat(user_id)
    
    return id

@dataclass(frozen=True, kw_only=True)
class MetaUser:
    MAX_NAME_LENGTH: ClassVar[int] = 32

    id: int
    meta_rank: MetaRank
    name: str

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,)

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity


@dataclass(frozen=True, kw_only=True)
class CommunityUser:
    user: MetaUser
    community: 'Community'
    community_rank: CommunityRank
    selected_list: 'List | None'
    
    @property
    def meta_rank(self) -> MetaRank:
        return self.user.meta_rank
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (*self.user.identity, self.community.id)
    
    @property
    def highest_rank(self) -> CommunityRank | MetaRank:
        return self.meta_rank or self.community_rank
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    
    
    
@dataclass(frozen=True, kw_only=True)
class ServerUser:
    community_user: CommunityUser
    server_rank: ServerRank

    @property
    def user(self) -> MetaUser:
        return self.community_user.user
    
    @property
    def meta_rank(self) -> MetaRank:
        return self.community_user.meta_rank
    
    @property
    def community_rank(self) -> CommunityRank:
        return self.community_user.community_rank
    
    @property
    def identity(self) -> tuple[int, ...]:
        return self.user.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity