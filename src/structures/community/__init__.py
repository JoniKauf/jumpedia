from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, NamedTuple, Self, TypedDict, Unpack
from database.simple_orm import Arg, Rows
from errors.feedback import FeedbackError, feedbacks
from ranks.community_rank import CommunityRank
from structures import attributes, task
from structures.attributes.slot_type import SlotType
from structures.attributes.static_attribute import StaticAttribute
from structures import BaseStructure
import structures.errors

from structures.list import List
from structures.user import JumpediaUser
from structures.user.community_user import CommunityUser
from utils import text
from database import queries, typed

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia
 

ListTbl = typed.List
CommunityTbl = typed.Community
CommunityUserTbl = typed.CommunityUser

@dataclass
class CommunityDataCache:
    server_ids: frozenset[int] | None = None


class CommunityLimits(NamedTuple):
    community_list_count_max: int
    list_attribute_count_max: int
    list_task_count_max: int
    attribute_alias_count_max = 31
    attribute_slot_count_max = 32
    attribute_collection_entry_alias_count_max: int = 7



class Community(BaseStructure):
    __structure_name__ = "community"

    jumpedia: 'Jumpedia'
    id: int
    name: text.RealStr
    limits: CommunityLimits

    _cache: CommunityDataCache = field(init=False, default_factory=CommunityDataCache)

    def get_server_ids(self) -> frozenset[int]:
        if self._cache.server_ids is not None:
            return self._cache.server_ids
        
        ServerTbl = typed.Server
        
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {ServerTbl.id}
                FROM {ServerTbl}
                WHERE {ServerTbl.community_id} = {arg(self.id)}
            """)

            result = c.fetchall(ServerTbl)

        self._cache.server_ids = frozenset(row.id for row in result)

        return self._cache.server_ids
        
    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.jumpedia.identity
    
    def create_list(self, raw_name: str) -> 'List':
        with self.locked:
            real_name, norm_name = text.raw_to_real_and_norm(raw_name)
            del raw_name

            if self.get_list_by_name(norm_name) is not None:
                raise feedbacks.temp("A list with that name already exists")
            
            count = len(self.get_lists())

            if count >= self.limits.community_list_count_max:
                raise feedbacks.temp("Limit of lists reached", count)
            
            with queries.connected() as c:
                c.execute(lambda arg: t"""
                    INSERT INTO {ListTbl} (
                        {ListTbl.community_id},
                        {ListTbl.norm_name},
                        {ListTbl.real_name}
                    ) 
                    VALUES (
                        {arg(self.id)},
                        {arg(norm_name)},
                        {arg(real_name)}
                    )
                """)
                
                list_id = c.last_generated_id

                list = List(
                    community=self,
                    id=list_id,
                    name=real_name
                )

                list.create_attribute(
                    StaticAttribute,
                    'id',
                    frozenset(),
                    SlotType.INT,
                    1,
                    min_slots=1
                )

                list.create_attribute(
                    StaticAttribute,
                    'name',
                    frozenset(),
                    SlotType.STR,
                    1,
                    min_slots=1
                )

                list.create_attribute(
                    StaticAttribute,
                    'aliases',
                    frozenset(),
                    SlotType.STR,
                    self.limits.attribute_slot_count_max,
                    min_slots=1
                )

            return list
            
    def delete_list(self, id: int) -> None:
        with self.locked, queries.connected() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {ListTbl}
                WHERE 
                    {ListTbl.community_id} = {arg(self.id)}
                    AND {ListTbl.id} = {arg(id)}
            """)

            if c.affected_row_count <= 0:
                raise structures.errors.StructureNotFoundError

    def _fetch_from_list_table(self, where: Callable[[Arg], str] | None) -> Rows[ListTbl]:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {ListTbl}
                WHERE 
                    {ListTbl.community_id} = {arg(self.id)}
                    {f"AND {where(arg)}" if where is not None else ""}
            """)

            result = c.fetchall(ListTbl)

        return result
    
    def _list_row_to_obj(self, row: ListTbl) -> List:
        return List(
            community=self,
            id=row.id,
            name=row.real_name
        )
    
    def get_lists(self, where: Callable[[Arg], str] | None = None) -> list[List]:
        return [
            self._list_row_to_obj(data) 
            for data in self._fetch_from_list_table(where)
        ]

    def get_list_by_id(self, id: int) -> List | None:
        data = self._fetch_from_list_table(lambda arg: f"{ListTbl.id} = {arg(id)}")
        return self._list_row_to_obj(data[0]) if data else None
    
    def get_list_by_name(self, norm_name: text.NormStr) -> List | None:
        data = self._fetch_from_list_table(lambda arg: f"{ListTbl.norm_name} = {arg(norm_name)}")
        return self._list_row_to_obj(data[0]) if data else None
    
    def get_default_selected_list(self) -> List | None:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT {typed.Community.default_selected_list_id}
                FROM {typed.Community}
                WHERE 
                    {typed.Community.id} = {arg(self.id)}
            """)

            row = c.fetchone(typed.Community)

        if row is None or row.default_selected_list_id is None:
            return None

        return self.get_list_by_id(row.default_selected_list_id)
    
    def set_default_selected_list(self, list_id: int | None) -> None:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                UPDATE {CommunityTbl} 
                SET {CommunityTbl.default_selected_list_id} = {arg(list_id)}
                WHERE {CommunityTbl.id} = {arg(self.id)}
            """)

    def get_or_create_community_user(
        self, 
        jumpedia_user: JumpediaUser, 
        community_rank: CommunityRank, 
        selected_list_id: int | None, 
        override_community_rank_if_user_exists: bool,
        override_selected_list_if_user_exists: bool
    ) -> CommunityUser:
        with self.locked:
            community_user = self.get_community_user(jumpedia_user)
            
            with queries.connected() as c:
                # User doesn't exist yet
                if community_user is None:
                    c.execute(lambda arg: t"""
                        INSERT INTO {CommunityUserTbl} (
                            {CommunityUserTbl.community_id},
                            {CommunityUserTbl.user_id},
                            {CommunityUserTbl.power},
                            {CommunityUserTbl.selected_list_id}
                        )
                        VALUES (
                            {arg(self.id)},
                            {arg(jumpedia_user.id)},
                            {arg(community_rank.power)},
                            {arg(selected_list_id)}
                        )
                    """)

                else:
                    community_rank = community_rank if override_community_rank_if_user_exists else community_user.community_rank
                    selected_list_id = selected_list_id if override_selected_list_if_user_exists else community_user.selected_list_id

                    if community_rank != community_user or selected_list_id != selected_list_id:
                        c.execute(lambda arg: t"""
                            UPDATE {CommunityUserTbl}
                            SET 
                                {CommunityUserTbl.power} = {arg(community_rank.power)}
                                {CommunityUserTbl.selected_list_id} = {arg((None if selected_list_id is None else selected_list_id))}
                            WHERE 
                                {CommunityUserTbl.community_id} = {arg(self.id)}
                                AND {CommunityUserTbl.user_id} = {arg(jumpedia_user.id)}
                        """) 

            return CommunityUser(
                community=self,
                jumpedia_user=jumpedia_user,
                community_rank=community_rank,
                selected_list_id=selected_list_id
            )

    
    def get_community_user(self, jumpedia_user: JumpediaUser) -> CommunityUser | None:
        with queries.connected() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {CommunityUserTbl}
                WHERE 
                    {CommunityUserTbl.community_id} = {arg(self.id)}
                    AND {CommunityUserTbl.user_id} = {arg(jumpedia_user.id)}
            """)

            result = c.fetchone(CommunityUserTbl)

        if result is None:
            return None
        
        return CommunityUser(
            community=self,
            jumpedia_user=jumpedia_user,
            community_rank=CommunityRank.get(result.power),
            selected_list_id=result.selected_list_id
        )