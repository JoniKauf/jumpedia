from dataclasses import dataclass, field
import re

from database import queries
from typing import TYPE_CHECKING, Callable, ClassVar, Final, Self, TypedDict

from discordtools import feedbackerrors as fbe
import discord as dc

from structures.ranks import _RankBase, AnyRank, GuildRank, MetaRank, CommunityRank
from structures.context import Context

if TYPE_CHECKING:
    from structures.list import List
    from structures.community import Community



_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')

type UserIdentifierT = int | str | User | dc.User | dc.Member


def extract_id(user: UserIdentifierT) -> int:
    if isinstance(user, (str, int)):
        return _user_id_to_int(user)
    elif isinstance(user, (User, dc.User, dc.Member)):
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

    community: 'Community'
    id: int
    user_rank: CommunityRank
    meta_rank: MetaRank
    selected_list: 'List | None'
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.community.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    
    
@dataclass(frozen=True, kw_only=True)
class Actor:
    community: 'Community | None'
    id: int
    interaction: dc.Interaction
    meta_rank: MetaRank
    user_rank: CommunityRank
    guild_rank: GuildRank
    selected_list: 'List | None'
    
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + (
            self.community.identity 
            if self.community is not None 
            else (-1,)
        )
    
    @classmethod
    def create_or_get(cls, interaction: dc.Interaction) -> 'Actor':
        from structures.jumpedia import Jumpedia
        
        actor = interaction.user

        jumpedia = Jumpedia()
        meta_rank = jumpedia.get_meta_rank_by_user_id(actor.id)

        if isinstance(actor, dc.User) or (community := jumpedia.get_community_by_guild_id(actor.guild.id)) is None:
            return cls(
                community=None,
                id=actor.id,
                interaction=interaction,
                meta_rank=meta_rank,
                user_rank=CommunityRank.DEFAULT,
                guild_rank=GuildRank.DEFAULT,
                selected_list=None
            )

        user_rank = CommunityRank.DEFAULT

        with community.edit_lock:
            user = community.get_user_by_id(actor.id)

            if user is not None:
                user_rank = user.user_rank
            else:
                h = queries.ArgHelper()

                with queries.connected() as (conn, cursor):
                    cursor.execute(f"""
                        INSERT INTO user (
                            id,
                            community_id,
                            power
                        )
                        VALUES (
                            {h|actor.id},
                            {h|community.id},
                            {h|user_rank.power}
                        )
                    """, h.steal())

        return cls(
            community=community,
            id=actor.id,
            interaction=interaction,
            meta_rank=meta_rank,
            user_rank=user_rank,
            guild_rank=GuildRank.get_from_discord_user(actor),
            selected_list=user.selected_list if user is not None else None
        )

    def permitted(self, required_rank: AnyRank) -> bool:
        if isinstance(required_rank, MetaRank):
            return self.meta_rank >= required_rank
        
        if isinstance(required_rank, CommunityRank):
            if self.user_rank >= required_rank:
                return True
        else:
            if self.guild_rank >= required_rank:
                return True
        
        # Any Meta Rank is more powerful than the others besides NONE
        return self.meta_rank is not MetaRank.NONE