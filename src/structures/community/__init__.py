from contextlib import _GeneratorContextManager
from dataclasses import dataclass, field
from functools import cached_property
from threading import RLock
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Self, TypedDict, Unpack
import discord as dc

import mariadb
from errors import FeedbackError
from ranks.community_rank import CommunityRank
from structures import attributes, task
from structures.base_structure import BaseStructure
from structures.attributes import AttributeValueType
from structures.attributes.static_attribute import StaticAttribute
from structures.list.list import List
from structures.task.task import Task
from structures.users.community_user import CommunityUser
from utils import metautils, required, text
from database import queries, typed as typed
from database.typed import Tables as TBL
from typing import Optional as Opt
import structures.list as list_package
from discordtools import messaging as msg

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia
 

MAX_NAME_LENGTH: int = 64

@dataclass(frozen=True, kw_only=True)
class Community(BaseStructure):
    __structure_name__ = "community"

    MAX_LISTS: ClassVar[int] = 1

    jumpedia: 'Jumpedia'
    id: int
    name: str
    default_selected_list_id: int | None

    _server_ids: frozenset[int] | None = field(init=False, default=None)

    def _post_set_server_ids(self, value: frozenset[int]) -> None:
        object.__setattr__(self, '_server_ids', value)

    def get_server_ids(self) -> frozenset[int]:
        if self._server_ids is None:
            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    SELECT {TBL.Server.id}
                    FROM {TBL.Server}
                    WHERE {TBL.Server.community_id} = {h|self.id}
                """, h.steal())

                result: typed.ManyTableRowT = cursor.fetchall()

            self._post_set_server_ids(frozenset(row[TBL.Server.id] for row in result))
            assert self._server_ids is not None
            
        return self._server_ids
        
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.jumpedia.identity
    
    def create_list(self, name: str) -> 'List':
        with self.locked:
            if text.norm_syn(name).endswith(List.__structure_name__):
                raise FeedbackError(
                    f"Name Ends In {List.__structure_name__.title()}",
                    f"The specified name for the {List.__structure_name__.lower()}"
                )
            
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
                    task.STATIC_NAME_ATTRIBUTE_NAME,
                    (),
                    AttributeValueType.get_by_type(str),
                    1,
                    1,
                    True,
                    True
                )

                list.create_static_attribute(
                    task.STATIC_ALIASES_ATTRIBUTE_NAME,
                    (),
                    AttributeValueType.get_by_type(str),
                    1,
                    attributes.MAX_SLOTS,
                    True,
                    True
                )

            return list
            
            
    def delete_list_by_name(self, name: str) -> None:
        with self.locked:
            list = self.get_list_by_name(name)

            # Check if list already deleted, but object used
            if list is None:
                return
                
            h = queries.ArgHelper()

            with list.locked, queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM {TBL.List}
                    WHERE {TBL.List.id} = {h|list.id}
                """, h.steal())

                cursor.rowcount


    def _fetch_from_list_table(self, where: Callable[[queries.ArgHelper], str] | None) -> typed.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.List}
                WHERE {TBL.List.community_id} = {h|self.id}
                {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        return result
    
    def _list_data_to_obj(self, data: typed.SingleTableRowT) -> List:
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
    
    def set_default_selected_list(self, list_id: int | None) -> None:
        from utils import required
        
        h = queries.ArgHelper()

        with self.locked:
            if list_id is None:
                list_id = None
            else:
                list_id = required.structure_not_none(self.get_list_by_id(list_id), List).id
            
            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    UPDATE {TBL.Community} 
                    SET {TBL.Community.default_selected_list_id} = {h|list_id}
                    WHERE {TBL.Community.id} = {h|self.id}
                """, h.steal())
    
    def create_or_get_community_user(self, user_id: int, user_name: str, repl_community_rank: CommunityRank | None = None) -> CommunityUser:
        with self.locked:
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
                                AND {TBL.CommunityUser.user_id} = {h|community_user.meta_user.id}
                        """, h.steal())
                    else:
                        community_rank = community_user.community_rank 

                return CommunityUser(
                    meta_user=user,
                    community=self,
                    community_rank=community_rank,
                    selected_list=selected_list
                )

    def change_community_user_community_rank(self, user_id: int, user_name: str, community_rank: CommunityRank) -> None:
        with self.locked:
            self.create_or_get_community_user(user_id, user_name)

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    UPDATE {TBL.CommunityUser}
                    SET {TBL.CommunityUser.power} = {h|community_rank.power}
                    WHERE {TBL.CommunityUser.user_id} = {h|user_id}
                """, h.steal())

    def _fetch_from_community_user_table(self, where: Callable[[queries.ArgHelper], str] | None) -> typed.ManyTableRowT:
        h = queries.ArgHelper()
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {TBL.CommunityUser}
                WHERE 
                    {TBL.CommunityUser.community_id} = {h|self.id}
                    {f"AND {where(h)}" if where is not None else ""}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        return result
    
    def _community_user_data_to_obj(self, data: typed.SingleTableRowT) -> 'CommunityUser':  
        return CommunityUser(
            community=self,
            meta_user=self.jumpedia.create_or_get_user(data[TBL.CommunityUser.user_id], None),
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
    
    def add_to_server(self, server_id: int) -> 'Community':
        with self.jumpedia.locked:
            existing_community = self.jumpedia.get_community_by_server_id(server_id)

            if existing_community is not None:
                if self == existing_community:
                    raise FeedbackError(
                        "Server Already Connected To Specified Community",
                        f"This server is already connected to the specified community ({msg.code(self.name)})!"
                    )
                
                connect_cmd = cogs.meta.MetaCog.connect_community.qualified_name
                disconnect_cmd = cogs.meta.MetaCog.disconnect_community.qualified_name

                raise FeedbackError(
                    "Server Already Connected To A Community",
                    f"This server is already connected to a different community called {msg.code(existing_community.name)}!",
                    additional="A server can only be connected to one community at a time.",
                    paragraphs=[
                        f"If you want to change the community for this server, see the commands "
                        f"{msg.code(connect_cmd)} and {msg.code(disconnect_cmd)}."
                    ]
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

        return required.structure_not_none(
            self.jumpedia.get_community_by_id(self.id),
            Community
        )

    def remove_from_server(self, server_id: int) -> 'Community':
        with self.locked, self.jumpedia.locked:
            existing_community = self.jumpedia.get_community_by_server_id(server_id)

            required.server_with_community(existing_community)

            h = queries.ArgHelper()

            with queries.connected() as (conn, cursor):
                cursor.execute(f"""
                    DELETE FROM {TBL.Server}
                    WHERE {TBL.Server.id} = {h|server_id}
                """, h.steal())

        return required.structure_not_none(
            self.jumpedia.get_community_by_id(self.id),
            Community
        )

            