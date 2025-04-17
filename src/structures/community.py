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
from structures.list import List
from structures import list as list_module

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia

class CommunityTableT(TypedDict, total=True):
    id: int
    name: str
    display_name: str
    database_name: str

@dataclass(frozen=True, kw_only=False)
class Community:
    jumpedia: Jumpedia
    id: int
    name: str
    display_name: str
    database_name: str

    edit_lock: RLock = field(init=False, default_factory=RLock)

    MAX_NAME_LENGTH: ClassVar[int] = 50
    DATABASE_PREFIX: ClassVar[str] = "c_"
    META_TABLE_NAME: ClassVar[str] = "community"
    
    def __hash__(self) -> int:
        return hash(self.id)

    def create_list(self, bad_name: str) -> List:
        with self.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True, 
                Community.MAX_NAME_LENGTH,
                (list.name for list in self.get_lists())
            )
            
            INVALID_ENDING = List.__name__.lower()

            if name.endswith(INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out `{INVALID_ENDING}` from the name, as it is redundant!")
            
            with queries.connected(self) as (conn, cursor):
                cursor.execute(f"""
                    SELECT *
                    FROM ?
                    WHERE name = ?
                """, [List.TABLE_NAME, name])

                result_opt: Opt[list_module.ListTableT] = cursor.fetchone()

                if result_opt:
                    raise fbe.TemporaryFeedbackError(f"{List.TABLE_NAME.title()} with that name exists already")
                
                cursor.execute("""
                    INSERT INTO ?
                    (name, display_name)
                    VALUES (?, ?)
                """, [List.TABLE_NAME, name, display_name])
            
            obj = List(
                cursor.lastrowid,  # type: ignore
                name,
                display_name,
                self
            ) 

            return obj
    
    def get_lists(self) -> list[List]:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ?
            """, [List.TABLE_NAME])

            result: list[list_module.ListTableT] = cursor.fetchall()

        lists: list[List] = []

        for l_data in result:
            lists.append(List(
                l_data['id'],
                l_data['name'],
                l_data['display_name'],
                self
            ))

        return lists
    
    def _get_community(self, data: Opt[list_module.ListTableT]) -> List:
        if data is None:
            raise fbe.TemporaryFeedbackError("Community does not exist!")
        
        return List(
            community=self,
            id=data['id'],
            name=data['name'],
            display_name=data['display_name']
        )
    
    def get_community_by_id(self, id: int) -> List:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ? WHERE id = ?
            """, [List.TABLE_NAME, id])

            result: Opt[list_module.ListTableT] = cursor.fetchone()

        return self._get_community(result)
        
    def get_community_by_name(self, name: str) -> List:
        name = text.norm(name)

        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ? WHERE name = ?
            """, [List.TABLE_NAME, name])

            result: Opt[list_module.ListTableT] = cursor.fetchone()

        return self._get_community(result)