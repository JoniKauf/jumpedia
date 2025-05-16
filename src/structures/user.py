from dataclasses import dataclass
import re

from database import queries
from typing import TYPE_CHECKING, Callable, ClassVar, Final, TypedDict

from discordtools import feedbackerrors as fbe
import discord as dc

from structures.ranks import UserRank
from structures.context import Context

if TYPE_CHECKING:
    from structures.list import List
    from structures.community import Community



_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')

type UserIdentifierT = int | str | 'User' | dc.User | dc.Member

@dataclass(frozen=True, kw_only=True)
class User:
    MAX_NAME_LENGTH: ClassVar[int] = 32

    community: 'Community | None'
    id: int
    user_rank: 'UserRank'
    selected_list: 'List | None'

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + (0,)
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    @classmethod
    def _get(cls, community: 'Community', id: int) -> 'User':
        meta_user_rank = UserRank.get_meta_from_user_id(id)
        user = community.get_user_by_id(id)
        
        if meta_user_rank is None:
            return user or cls(
                community=community,
                id=id,
                user_rank=UserRank.DEFAULT,
                selected_list=None
            )
        
        return cls(
            community=community,
            id=id,
            user_rank=meta_user_rank,
            selected_list=user.selected_list if user is not None else None
        )

    @classmethod 
    def _get_or_create(cls, community: 'Community | None', id: int) -> 'User':
        # TODO lock here for id, not critical but avoids exceptions
        where_id_equal: Callable[[queries.ArgHelper], str] = lambda h: f"id = {h|id}"
        
        important_data = UserRank.get_meta_from_user_id(id)

        if community is None:
            return cls(
                community=None,
                id=id,
                user_rank=important_data or UserRank.DEFAULT,
                selected_list=None
            )
        
        secondary_data = community._fetch_from_user_table(where_id_equal)

        selected_list: None | List = None
        selected_list_id: None | int = None

        if secondary_data and (selected_list_id := secondary_data[0]['selected_list_id']) is not None:
            selected_list = community.get_list_by_id(selected_list_id)

        # If user already in community's database
        if secondary_data is not None:
            user_data = secondary_data[0]

            return cls(
                community=community,
                id=user_data['id'],
                user_rank=UserRank.get(user_data['power']),
                selected_list=selected_list
            )

        h = queries.ArgHelper()

        with queries.connected(community) as (conn, cursor):
            cursor.execute(f"""
                INSERT INTO user
                (id, power, selected_list_id)
                VALUES
                ({h|id}, {h|UserRank.DEFAULT.power}, {h|selected_list_id})
            """, h.steal())

            return cls(
                community=community,
                id=id,
                user_rank=UserRank.DEFAULT,
                selected_list=None
            )
    
    # Because we have a context, we can be sure the actor exists and therefore
    # we always save them. The other person might not exist due to us only
    # having their id, therefore we only try to get them.
    @classmethod
    def get_actor(cls, ctx: Context) -> 'User':
        return cls._get_or_create(ctx.community, ctx.ia.user.id)
    
    @classmethod
    def get_other(cls, ctx: 'Context | Community', other_user: UserIdentifierT) -> 'User | None':
        other_id = cls.find_id(other_user)

        if isinstance(ctx, Context):
            cls.get_actor(ctx)
            return cls._get(ctx.community, other_id) if ctx.community is not None else None
        
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