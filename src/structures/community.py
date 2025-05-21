from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Self, TypedDict, Unpack
import discord as dc

import mariadb
from utils import metautils, text
from database import queries, strong as S
from database.strong import Tables as TBL
import discordtools.feedbackerrors as fbe
from typing import Optional as Opt

from structures.list import List
from structures.user import User
from structures.ranks import GuildRank, CommunityRank
from utils.locked import equality_locked

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia
 
@dataclass(kw_only=True)
class Community:
    MAX_NAME_LENGTH: ClassVar[int] = 64
    MAX_LISTS: ClassVar[int] = 1
    DATABASE_PREFIX: ClassVar[str] = "community_".lower()
    INVALID_ENDING: ClassVar[str] = "community".lower()

    jumpedia: 'Jumpedia'
    id: int
    name: str
    default_selected_list_id: int | None

    _guild_ids: set[int] | None = field(init=False, default=None)

    def get_guild_ids(self) -> set[int]:
        if self._guild_ids is None:
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {TBL.Guild.id}
                    FROM {TBL.Guild}
                    WHERE {TBL.Guild.community_id} = {h|self.id}
                """)

                result: S.ManyTableRowT = cursor.fetchall()

            self._guild_ids = {row[TBL.Guild.id] for row in result}

        return self._guild_ids
        
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.jumpedia.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    def create_list(self, bad_name: str) -> 'List':
        with equality_locked(self):
            lists = self.get_lists()

            if name.endswith(List.INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out `{List.INVALID_ENDING}` from the name, as it is redundant!")
            
            if len(lists) >= Community.MAX_LISTS:
                raise fbe.TemporaryFeedbackError("Limit reached")
            
            h = queries.ArgHelper()

            with queries.connected(cursor) as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO list (
                        name
                    ) 
                    VALUES (
                        {h|name}
                    )
                """, h.steal())
                
                id: int = cursor.lastrowid  # type: ignore

                obj = List(
                    community=self,
                    id=id,
                    name=name
                )

            return obj
            
            
    def delete_list(self, bad_name: str) -> None:
        with equality_locked(self):
            list = self.get_list_by_name(bad_name)

            # Check if list already deleted, but object used
            if list is None:
                return
                
            h = queries.ArgHelper()

            with equality_locked(list), queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM list
                    WHERE id = {h|self.id}
                """, h.steal())


    def _fetch_from_list_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[ListResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM list
                WHERE community_id = {h|self.id}
                {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[ListResultT] = cursor.fetchall()

        return result
    
    def _list_data_to_obj(self, data: ListResultT) -> List:
        if data is None:
            return None
        
        return List(
            community=self,
            id=data['id'],
            name=data['name']
        )
    
    def get_lists(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[List]:
        return [
            self._list_data_to_obj(data) 
            for data in self._fetch_from_list_table(where)
        ]

    def get_list_by_id(self, id: int) -> List | None:
        data = self._fetch_from_list_table(lambda h: f"id = {h|id}")
        return self._list_data_to_obj(data[0]) if data else None
    
    def get_list_by_name(self, name: str) -> List | None:
        name = text.norm(name)
        data = self._fetch_from_list_table(lambda h: f"id = {h|name}")
        return self._list_data_to_obj(data[0]) if data else None
    
    def get_default_selected_list(self) -> List | None:
        if self.default_selected_list_id is None:
            return None
        
        return self.get_list_by_id(self.default_selected_list_id)
            
    def _fetch_from_user_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[UserResultT]:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM user
                WHERE community_id = {h|self.id}
                {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list['UserResultT'] = cursor.fetchall()

        return result
    
    def _user_data_to_obj(self, data: UserResultT) -> 'User':  
        id = data['id']

        return User(
            community=self,
            id=id,
            user_rank=CommunityRank.get(data['power']),
            meta_rank=self.jumpedia.get_meta_rank_by_user_id(id),
            selected_list=self.get_default_selected_list()
        )
    
    def get_users(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[User]:
        return [
            self._user_data_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_user_by_id(self, id: int) -> 'User | None':
        data = self._fetch_from_user_table(lambda h: f"id = {h|id}")
        return self._user_data_to_obj(data[0]) if data else None
    
    def add_to_guild(self, guild_id: int) -> None:
        with equality_locked(self.jumpedia):
            existing_community = self.jumpedia.get_community_by_guild_id(guild_id)

            if existing_community is not None:
                if self == existing_community:
                    raise fbe.TemporaryFeedbackError(
                        f"Your server already hosts this community."
                    )
                
                raise fbe.TemporaryFeedbackError(
                    f"Your server already hosts the community {existing_community.name}."
                )
            
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO guild (
                        id,
                        community_id
                    )
                    VALUES (
                        {h|guild_id},
                        {h|self.id}
                    )
                """, h.steal())

            varname = metautils.varname(f"{self.guild_ids=}", False)
            object.__setattr__(self, varname, self.guild_ids.union([guild_id]))

    
    def remove_from_guild(self, guild_id: int) -> None:
        with equality_locked(self.jumpedia):
            existing_community = self.jumpedia.get_community_by_guild_id(guild_id)

            if existing_community is None:
                fbe.TemporaryFeedbackError("This server doesn't host a community.")

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM guild
                    WHERE id = {h|guild_id}
                """, h.steal())
            