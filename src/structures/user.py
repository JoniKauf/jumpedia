from dataclasses import dataclass
import re

from database import queries
from typing import TYPE_CHECKING, ClassVar, TypedDict

from discordtools import feedbackerrors as fbe

import discord as dc

from structures.ranks import UserRank
from structures.community import Community
from structures.context import Context
from structures.list import List

_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')

type UserIdentifierT = int | str | 'User' | dc.User | dc.Member

class UserResultT(TypedDict):
    id: int
    power: int
    selected_list_id: int | None

@dataclass(frozen=True, kw_only=True)
class User:
    MAX_NAME_LENGTH: ClassVar[int] = 32

    community: Community
    id: int
    user_rank: UserRank
    selected_list: List | None

    def __hash__(self) -> int:
        return hash((self.id, hash(self.community)))
    
    def __eq__(self, value: object) -> bool: 
        return isinstance(value, User) and self.id == value.id and self.community == value.community
    
    @classmethod
    def _get(cls, community: Community, id: int) -> 'User':
        result = community._fetch_users_from_table(lambda h: f"id = {h|id}")

        if not result:
            raise fbe.TemporaryFeedbackError("Person does not exist")
        
        return community._user_data_to_obj(result[0])

    @classmethod 
    def _get_or_create(cls, community: Community, id: int, user_rank: UserRank = UserRank.USER, selected_list: List | None = None) -> 'User':
        h = queries.ArgHelper()

        result = community._fetch_users_from_table(lambda h: f"id = {h|id}")

        with queries.connected(community) as (conn, cursor):
            # TODO lock per id, not critical but avoids exceptions
            if not result:
                cursor.execute(f"""
                    INSERT INTO user
                    (id, power, selected_list_id)
                    VALUES
                    ({h|id}, {h|user_rank.power}, {h|(None if selected_list is None else selected_list.id)})
                """, h.steal())
  
                return cls(
                    community=community,
                    id=id,
                    user_rank=user_rank,
                    selected_list=selected_list
                )
        
        return community._user_data_to_obj(result[0])
    
    # Because we have a context, we can be sure the actor exists and therefore
    # we always save them. The other person might not exist due to us only
    # having their id, therefore we only try to get them.
    @classmethod
    def get_actor(cls, ctx: Context) -> 'User':
        return cls._get_or_create(ctx.community, ctx.interaction.user.id)
    
    @classmethod
    def get_other(cls, ctx: Context, other_user: UserIdentifierT) -> 'User':
        return cls.get_both(ctx, other_user)[1]
    
    @classmethod
    def get_both(cls, ctx: Context, other_user: UserIdentifierT) -> tuple['User', 'User']:
        actor = cls.get_actor(ctx)
        other = cls._get(ctx.community, cls.find_id(other_user))
        return (actor, other)

    @classmethod
    def find_id(cls, user: UserIdentifierT) -> int:
        if isinstance(user, (str, int)):
            return cls._user_id_to_int(user)
        elif isinstance(user, (cls, dc.User, dc.Member)):
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
    
