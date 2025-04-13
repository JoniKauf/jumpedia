from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, ClassVar, Self, TypedDict, Unpack
from threading import RLock

import mariadb
from structures.attribute import Attribute
from utils import text
from database import queries
import discordtools.feedbackerrors as fbe
from typing import Optional as Opt
from structures.list import List, ListTableT

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia

class CommunityTableT(TypedDict, total=True):
    id: int
    name: str
    display_name: str
    database_name: str

@dataclass(frozen=True, kw_only=False)
class Community:
    id: int
    name: str
    display_name: str
    database_name: str
    jumpedia: Jumpedia

    lists: set[List] = field(init=False, default_factory=set)
    list_id_mapping: dict[int, List] = field(init=False, default_factory=dict)
    list_name_mapping: dict[str, List] = field(init=False, default_factory=dict)
    edit_lock: RLock = field(init=False, default_factory=RLock)

    MAX_NAME_LENGTH: ClassVar[int] = 50
    DATABASE_PREFIX: ClassVar[str] = "c_"
    META_TABLE_NAME: ClassVar[str] = "community"

    def __post_init__(self) -> None:
        self.reload_lists()
    
    def __hash__(self) -> int:
        return hash(self.id)

    def reload_lists(self) -> None:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ?
            """, [List.TABLE_NAME])

            result: list[ListTableT] = cursor.fetchall()

        with self.edit_lock:
            self.lists.clear()
            self.list_id_mapping.clear()
            self.list_name_mapping.clear()

            for l_data in result:
                self._add_to_list_collection(List(
                    l_data['id'],
                    l_data['name'],
                    l_data['display_name'],
                    self
                ))

    def _add_to_list_collection(self, list: List):
        with self.edit_lock:
            self.lists.add(list)
            self.list_id_mapping[list.id] = list
            self.list_name_mapping[list.name] = list

    def create_list(self, bad_name: str) -> List:
        with self.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True, 
                self.list_name_mapping
            )
            
            # They should be the same name because we lower and not casefold,
            # but just to make sure
            if any(len(n) > List.MAX_NAME_LENGTH for n in (name, display_name)):
                raise fbe.TemporaryFeedbackError("Too long name, max is 50 chars")
            
            if name.endswith(List.TABLE_NAME):
                raise fbe.TemporaryFeedbackError(f"Please leave out '{List.TABLE_NAME}' from you {List.TABLE_NAME}'s name, as it is redundant!")
            
            with queries.connected(self) as (conn, cursor):
                cursor.execute(f"""
                    SELECT *
                    FROM ?
                    WHERE name = ?
                """, [List.TABLE_NAME, name])

                result_opt: Opt[ListTableT] = cursor.fetchone()

                if result_opt:
                    raise fbe.TemporaryFeedbackError(f"{List.TABLE_NAME.title()} with that name exists already")
                
                cursor.execute("""
                    INSERT INTO ?
                    (name, display_name)
                    VALUES (?, ?)
                """, [List.TABLE_NAME, name, display_name])
                
                # To get id
                cursor.execute("""
                    SELECT * FROM ? WHERE name = ?
                """, [Community.META_TABLE_NAME, name])

                result: ListTableT = cursor.fetchone()
            
            obj = List(
                result['id'],
                result['name'],
                result['display_name'],
                self
            ) 

            self._add_to_list_collection(obj)

            return obj
    
    def get_list_by_id(self, id: int) -> List:
        try:
            return self.list_id_mapping[id]
        except KeyError as e:
            raise LookupError(*e.args)
        
    def get_list_by_name(self, name: str) -> List:
        try:
            return self.list_name_mapping[name]
        except KeyError as e:
            raise LookupError(*e.args)