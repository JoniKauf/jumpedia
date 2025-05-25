from dataclasses import dataclass, field
import re

from database import queries
from typing import TYPE_CHECKING, Callable, ClassVar, Final, Self, TypedDict

from discordtools import feedbackerrors as fbe
import discord as dc

from structures.ranks import _RankBase, AnyRank, ServerRank, MetaRank, CommunityRank
from structures.context import Context
from utils.locked import equality_locked

if TYPE_CHECKING:
    from structures.list import List
    from structures.community import Community



_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')

type UserIdentifierT = int | str | CommunityUser | dc.User | dc.Member


def extract_id(user: UserIdentifierT) -> int:
    if isinstance(user, (str, int)):
        return _user_id_to_int(user)
    elif isinstance(user, (CommunityUser, dc.User, dc.Member)):
        return user.id
    
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
class User:
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
    user: User
    community: 'Community'
    community_rank: CommunityRank
    selected_list: 'List | None'
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (*self.user.identity, self.community.id)
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    
    
@dataclass(frozen=True, kw_only=True)
class Interactor:
    interaction: dc.Interaction
    any_user: User | CommunityUser
    server_rank: ServerRank

    @property
    def user(self) -> User:
        return self.any_user if isinstance(self.any_user, User) else self.any_user.user
    
    @property
    def community_user(self) -> CommunityUser | None:
        return self.any_user if isinstance(self.any_user, CommunityUser) else None
    
    @property
    def identity(self) -> tuple[int, ...]:
        return self.user.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    @classmethod
    def create_or_get(cls, interaction: dc.Interaction) -> 'Interactor':
        from structures.jumpedia import Jumpedia
        
        dc_user = interaction.user

        jumpedia = Jumpedia()
        meta_rank = jumpedia.get_user_by_id(dc_user.id)

        if not isinstance(dc_user, dc.Member) or (community := jumpedia.get_community_by_server_id(dc_user.guild.id)) is None:
            return cls(
                community=None,
                id=dc_user.id,
                interaction=interaction,
                meta_rank=meta_rank,
                community_rank=CommunityRank.DEFAULT,
                server_rank=ServerRank.DEFAULT,
                selected_list=None
            )

        community_rank = CommunityRank.DEFAULT

        with equality_locked(community):
            user = community.get_user_by_id(dc_user.id)

            if user is not None:
                community_rank = user.community_rank
            else:
                h = queries.ArgHelper()

                with queries.connected() as (conn, cursor):
                    cursor.execute(f"""
                        INSERT INTO user (
                            id,
                            community_id,
                            name,
                            power
                        )
                        VALUES (
                            {h|dc_user.id},
                            {h|community.id},
                            {h|dc_user.display_name or dc_user.name},
                            {h|community_rank.power}
                        )
                    """, h.steal())

        return cls(
            community=community,
            id=dc_user.id,
            interaction=interaction,
            meta_rank=meta_rank,
            community_rank=community_rank,
            server_rank=ServerRank.get_from_discord_user(dc_user),
            selected_list=user.selected_list if user is not None else None
        )

    def permitted(self, required_rank: AnyRank) -> bool:
        if isinstance(required_rank, MetaRank):
            return self.meta_rank >= required_rank
        
        if isinstance(required_rank, CommunityRank):
            if self.community_rank >= required_rank:
                return True
        else:
            if self.server_rank >= required_rank:
                return True
        
        # Any Meta Rank is more powerful than the others besides NONE
        return self.meta_rank is not MetaRank.NONE