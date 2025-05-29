from dataclasses import dataclass, field
from functools import cached_property
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Self, TypedDict, Unpack
import discord as dc

import mariadb
from structures.attribute import AttributeValueType, StaticAttribute
from structures.task import Task
from utils import metautils, text
from database import queries, strong as S
from database.strong import Tables as TBL
import discordtools.feedbackerrors as fbe
from typing import Optional as Opt

from structures.list import List
from structures.users import CommunityUser, MetaUser
from structures.ranks import ServerRank, CommunityRank
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

    _server_ids: set[int] | None = field(init=False, default=None)

    def get_server_ids(self) -> set[int]:
        if self._server_ids is None:
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {TBL.Server.id}
                    FROM {TBL.Server}
                    WHERE {TBL.Server.community_id} = {h|self.id}
                """, h.steal())

                result: S.ManyTableRowT = cursor.fetchall()

            self._server_ids = {row[TBL.Server.id] for row in result}

        return self._server_ids
        
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.jumpedia.identity
    
    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    def create_list(self, bad_name: str) -> 'List':
        with equality_locked(self):
            name = text.validate_and_sanitize_name(
                bad_name,
                List.MAX_NAME_LENGTH
            )

            if name.endswith(List.INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out `{List.INVALID_ENDING}` from the name, as it is redundant!")
            
            if self.get_list_by_name(name) is not None:
                raise fbe.TemporaryFeedbackError("A list with that name already exists")
            
            if (count := len(self.get_lists())) >= Community.MAX_LISTS:
                raise fbe.TemporaryFeedbackError("Limit of lists reached", count)
            
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO {TBL.List} (
                        {TBL.List.community_id},
                        {TBL.List.name}
                    ) 
                    VALUES (
                        {h|self.id},
                        {h|name}
                    )
                """, h.steal())
                
                id: int = cursor.lastrowid  # type: ignore

                list = List(
                    community=self,
                    id=id,
                    name=name
                )

                list.create_static_attribute(
                    Task.STATIC_NAME_ATTRIBUTE_NAME,
                    (),
                    AttributeValueType.get_by_type(str),
                    1,
                    1,
                    True,
                    True
                )

                list.create_static_attribute(
                    Task.STATIC_ALIAS_ATTRIBUTE_NAME,
                    (),
                    AttributeValueType.get_by_type(str),
                    1,
                    StaticAttribute.MAX_SLOTS,
                    True,
                    True
                )

            return list
            
            
    def delete_list(self, bad_name: str) -> None:
        with equality_locked(self):
            list = self.get_list_by_name(bad_name)

            # Check if list already deleted, but object used
            if list is None:
                raise fbe.TemporaryFeedbackError("List not found")
                
            h = queries.ArgHelper()

            with equality_locked(list), queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM {TBL.List}
                    WHERE {TBL.List.id} = {h|self.id}
                """, h.steal())


    def _fetch_from_list_table(self, where: Callable[[queries.ArgHelper], str] | None) -> S.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.List}
                WHERE {TBL.List.community_id} = {h|self.id}
                {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: S.ManyTableRowT = cursor.fetchall()

        return result
    
    def _list_data_to_obj(self, data: S.SingleTableRowT) -> List:
        return List(
            community=self,
            id=data[TBL.List.id],
            name=data[TBL.List.name]
        )
    
    def get_lists(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[List]:
        return [
            self._list_data_to_obj(data) 
            for data in self._fetch_from_list_table(where)
        ]

    def get_list_by_id(self, id: int) -> List | None:
        data = self._fetch_from_list_table(lambda h: f"{TBL.List.id} = {h|id}")
        return self._list_data_to_obj(data[0]) if data else None
    
    def get_list_by_name(self, name: str) -> List | None:
        name = text.norm(name)
        data = self._fetch_from_list_table(lambda h: f"{TBL.List.name} = {h|name}")
        return self._list_data_to_obj(data[0]) if data else None
    
    def get_default_selected_list(self) -> List | None:
        if self.default_selected_list_id is None:
            return None
        
        return self.get_list_by_id(self.default_selected_list_id)
    
    
    def create_or_get_community_user(self, user_id: int, user_name: str, repl_community_rank: CommunityRank | None = None) -> CommunityUser:
        with equality_locked(self):
            community_user = self.get_community_user_by_id(user_id)
            user = self.jumpedia.create_or_get_user(user_id, user_name)

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                if community_user is None:
                    community_rank = repl_community_rank or CommunityRank.DEFAULT
                    selected_list = None

                    cursor.execute(f"""
                        INSERT INTO {TBL.CommunityUser} (
                            {TBL.CommunityUser.community_id},
                            {TBL.CommunityUser.user_id},
                            {TBL.CommunityUser.power},
                            {TBL.CommunityUser.selected_list_id}
                        )
                        VALUES (
                            {h|self.id},
                            {h|user_id},
                            {h|community_rank.power},
                            {h|selected_list}
                        )
                    """, h.steal())

                else:
                    community_rank = repl_community_rank or community_user.community_rank
                    selected_list = community_user.selected_list

                    if community_rank != community_user.community_rank:
                        cursor.execute(f"""
                            UPDATE {TBL.CommunityUser}
                            SET {TBL.CommunityUser.power} = {h|community_rank.power}
                            WHERE 
                                {TBL.CommunityUser.community_id} = {h|self.id}
                                AND {TBL.CommunityUser.user_id} = {h|community_user.user.id}
                        """, h.steal())
                    else:
                        community_rank = community_user.community_rank 

                return CommunityUser(
                    user=user,
                    community=self,
                    community_rank=community_rank,
                    selected_list=selected_list
                )

    def change_community_user_community_rank(self, user_id: int, user_name: str, community_rank: CommunityRank) -> None:
        with equality_locked(self):
            self.create_or_get_community_user(user_id, user_name)

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    UPDATE {TBL.CommunityUser}
                    SET {TBL.CommunityUser.power} = {h|community_rank.power}
                    WHERE {TBL.CommunityUser.user_id} = {h|user_id}
                """, h.steal())

    def _fetch_from_community_user_table(self, where: Callable[[queries.ArgHelper], str] | None) -> S.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.CommunityUser}
                WHERE 
                    {TBL.CommunityUser.community_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: S.ManyTableRowT = cursor.fetchall()

        return result
    
    def _community_user_data_to_obj(self, data: S.SingleTableRowT) -> 'CommunityUser':  
        return CommunityUser(
            community=self,
            user=self.jumpedia.create_or_get_user(data[TBL.CommunityUser.user_id], None),
            community_rank=CommunityRank.get(data[TBL.CommunityUser.power]),
            selected_list=self.get_list_by_id(data[TBL.CommunityUser.selected_list_id])
        )
    
    def get_community_users(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list[CommunityUser]:
        return [
            self._community_user_data_to_obj(data) 
            for data in self._fetch_from_community_user_table(where)
        ]

    def get_community_user_by_id(self, id: int) -> 'CommunityUser | None':
        data = self._fetch_from_community_user_table(lambda h: f"{TBL.CommunityUser.user_id} = {h|id}")
        return self._community_user_data_to_obj(data[0]) if data else None
    
    def add_to_server(self, server_id: int) -> None:
        with equality_locked(self.jumpedia):
            existing_community = self.jumpedia.get_community_by_server_id(server_id)

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
                    INSERT INTO {TBL.Server} (
                        {TBL.Server.id},
                        {TBL.Server.community_id}
                    )
                    VALUES (
                        {h|server_id},
                        {h|self.id}
                    )
                """, h.steal())

            self.get_server_ids().add(server_id)

    def remove_from_server(self, server_id: int) -> None:
        with equality_locked(self.jumpedia):
            existing_community = self.jumpedia.get_community_by_server_id(server_id)

            if existing_community is None:
                fbe.TemporaryFeedbackError("This server doesn't host a community.")

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM {TBL.Server}
                    WHERE {TBL.Server.id} = {h|server_id}
                """, h.steal())
            