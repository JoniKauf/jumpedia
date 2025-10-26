import builtins
import typing as t

from src.structures.jumpedia import db
from src.utils.orm.query import Operator

from ..utils.text import NormStr, RealStr
from . import BaseStructure, errors, list
from .attribute import StaticAttribute
from .attribute.slot_type import SlotType
from .list import List

if t.TYPE_CHECKING:
    from .jumpedia import Jumpedia

class CommunityLimits(t.NamedTuple):
    community_list_count_max: int
    list_attribute_count_max: int
    list_task_count_max: int
    attribute_alias_count_max: int
    attribute_collection_entry_count_max: int
    attribute_collection_entry_alias_count_max: int

class Community(BaseStructure):
    __structure_name__ = "community"

    jumpedia: 'Jumpedia'
    id: int
    real_name: RealStr
    norm_name: NormStr
    limits: CommunityLimits

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.jumpedia.identity
    
    @property
    def name(self) -> str:
        return self.real_name
    
    def get_server_ids(self) -> frozenset[int]:
        with self.jumpedia.connector.cursor() as c:
            rows = c.select(
                db.Server.id,
                from_=db.Server
            ).where(
                (db.Server.community_id, Operator.EQ, self.id)
            ).fetch_all()
        
        return frozenset(row.id for row in rows)
    
    def create_list(self, real_name: RealStr) -> 'List':
        norm_name = NormStr(real_name)
        
        with self.locked:
            list_ = self.get_list_by_name(norm_name)

            if list_ is not None:
                raise errors.SynAlreadyTakenError(real_name, list_)
            
            count = len(self.get_lists())

            if count >= self.limits.community_list_count_max:
                raise errors.LimitOfStructuresReachedError(self.limits.community_list_count_max, List)

            with self.jumpedia.connector.cursor() as c:
                execute_data = c.insert(
                    db.List.community_id.bind_n(self.id),
                    db.List.norm_name.bind_n(norm_name),
                    db.List.real_name.bind_n(real_name),
                    into=db.List
                ).execute(
                    get_last_generated_id=True
                )
                
                list_id = execute_data.last_generated_id
                assert list_id is not None
                
                list_ = List(
                    community=self,
                    id=list_id,
                    real_name=real_name,
                    norm_name=norm_name
                )

                list_.create_attribute(
                    StaticAttribute,
                    RealStr('Id'),
                    frozenset(),
                    SlotType.INT,
                    1,
                    min_slots=1,
                    kind=list.STATIC_ATTRIBUTE_KIND_OF_ID
                )

                list_.create_attribute(
                    StaticAttribute,
                    RealStr('Name'),
                    frozenset(),
                    SlotType.STR,
                    1,
                    min_slots=1,
                    kind=list.STATIC_ATTRIBUTE_KIND_OF_NAME
                )

                list_.create_attribute(
                    StaticAttribute,
                    RealStr('Aliases'),
                    frozenset(),
                    SlotType.STR,
                    self.jumpedia.limits.attribute_task_value_slot_count_max,
                    min_slots=1,
                    kind=list.STATIC_ATTRIBUTE_KIND_OF_ALIASES
                )

            return list_
            
    def delete_list(self, id: int) -> None:
        from . import errors

        with self.locked, self.jumpedia.connector.cursor() as c:
            c.execute(lambda arg: t"""
                DELETE FROM {typed.List}
                WHERE 
                    {typed.List.community_id} = {arg(self.id)}
                    AND {typed.List.id} = {arg(id)}
            """)

            if c.affected_row_count <= 0:
                raise errors.StructureNotFoundError(List)

    def _fetch_from_list_table(self, where: t.Callable[[Arg], str] | None) -> Rows[typed.List]:
        with self.jumpedia.connector.cursor() as c:
            c.execute(lambda arg: t"""
                SELECT *
                FROM {typed.List}
                WHERE 
                    {typed.List.community_id} = {arg(self.id)}
                    {Raw(f"AND {where(arg)}" if where is not None else "")}
            """)

            result = c.fetchall(typed.List)

        return result
    
    def _list_row_to_obj(self, row: typed.List) -> List:
        return List(
            community=self,
            id=row.id,
            real_name=row.real_name,
            norm_name=row.norm_name
        )
    
    def get_lists(self, where: t.Callable[[Arg], str] | None = None) -> builtins.list[List]:
        return [
            self._list_row_to_obj(data) 
            for data in self._fetch_from_list_table(where)
        ]

    def get_list_by_id(self, id: int) -> List | None:
        data = self._fetch_from_list_table(lambda arg: f"{typed.List.id} = {arg(id)}")
        return self._list_row_to_obj(data[0]) if data else None
    
    def get_list_by_name(self, norm_name: NormStr) -> List | None:
        data = self._fetch_from_list_table(lambda arg: f"{typed.List.norm_name} = {arg(norm_name)}")
        return self._list_row_to_obj(data[0]) if data else None
    
    def get_default_selected_list(self) -> List | None:
        with self.jumpedia.connector.cursor() as c:
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
        from . import errors
        with self.jumpedia.connector.cursor() as c:
            c.execute(lambda arg: t"""
                UPDATE {typed.Community} 
                SET {typed.Community.default_selected_list_id} = {arg(list_id)}
                WHERE {typed.Community.id} = {arg(self.id)}
            """)

            if c.affected_row_count < 1:
                raise errors.StructureNotFoundError(Community)