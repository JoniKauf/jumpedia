from dataclasses import dataclass
import re

from database import queries
from typing import TYPE_CHECKING, ClassVar, Final, TypedDict

from discordtools import feedbackerrors as fbe

import discord as dc

from structures.jumpedia import Jumpedia
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
    MAX_NAME_LENGTH: ClassVar[Final[int]] = 32
    JUMPEDIA: ClassVar['User'] = None  # type: ignore

    community: Community
    id: int
    user_rank: UserRank
    selected_list: List | None

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.community.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity
    
    @classmethod
    def _init(cls) -> None:
        cls.JUMPEDIA = User(
            community=Community(
                jumpedia=Jumpedia(),
                id=0,
                guild_ids=frozenset(),
                name="",
                display_name=""
            ),
            id=0,
            user_rank=UserRank.USER,
            selected_list=None
        )

    @classmethod
    def _get(cls, community: Community, id: int) -> 'User':
        if id == cls.JUMPEDIA.id:
            return cls.JUMPEDIA
        
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
    def get_other(cls, ctx: Context | Community, other_user: UserIdentifierT) -> 'User':
        other_id = cls.find_id(other_user)

        if isinstance(ctx, Context):
            cls.get_actor(ctx)
            return cls._get(ctx.community, other_id)
        
        return cls._get(ctx, other_id)
    
    @classmethod
    def get_both(cls, ctx: Context, other_user: UserIdentifierT) -> tuple['User', 'User']:
        return (cls.get_actor(ctx), cls.get_other(ctx.community, other_user))

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
    
    @classmethod
    def is_jumpedia(cls, user: UserIdentifierT) -> bool:
        return cls.find_id(user) == cls.JUMPEDIA_USER_ID
    
User._init()