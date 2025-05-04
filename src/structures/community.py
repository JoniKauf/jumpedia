from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar, Final, Self, TypedDict, Unpack
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

    MAX_NAME_LENGTH: ClassVar[Final[int]] = 50
    DATABASE_PREFIX: ClassVar[Final[str]] = "c_"
    META_TABLE_NAME: ClassVar[Final[str]] = __name__.lower()
    INVALID_ENDING: ClassVar[Final[str]] = __name__.lower()
    
    @classmethod
    def create(cls, jumpedia: Jumpedia, bad_name: str) -> 'Community':
        with jumpedia.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True,
                Community.MAX_NAME_LENGTH,
                (c.name for c in jumpedia.get_communities())
            )

            if name.endswith(cls.INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out '{cls.INVALID_ENDING}' from the name as it is redundant!")
            
            database_name = f"{Community.DATABASE_PREFIX}{name}"

            with queries.connected(jumpedia) as (conn, cursor):
                p = queries.ParamHelper()

                cursor.execute(f"""
                    SELECT *
                    FROM {p(Community.META_TABLE_NAME)}
                    WHERE name = {p(name)}
                """, p.params())

                result_opt: Opt[CommunityTableT] = cursor.fetchone()

                if result_opt:
                    raise fbe.TemporaryFeedbackError(f"{Community.META_TABLE_NAME.title()} with that name exists already")
                
                cursor.execute("""
                    INSERT INTO ?
                    (name, display_name, database_name)
                    VALUES (?, ?, ?)
                """, [Community.META_TABLE_NAME, name, display_name, database_name])
                
                obj = Community(
                    jumpedia,
                    cursor.lastrowid,  # type: ignore
                    name,
                    display_name,
                    database_name
                )  

                # If anything goes wrong here, exception will cause it to 
                # rollback step above, where we add the community to meta table
                obj._init_database()

            return obj
        
    def _init_database(self) -> None:
        with self.edit_lock:
            # Create database
            with queries.connected(None) as (conn, cursor):
                cursor.execute(f"CREATE DATABASE `{self.database_name}`")
            
            # If anything goes wrong here, delete database and raise error
            try:
                # Create tables
                with queries.connected(self):
                    cursor.execute("""
                        CREATE TABLE ? (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            community_id INT NOT NULL,
                            name VARCHAR(?) NOT NULL UNIQUE,
                            display_name VARCHAR(?) NOT NULL UNIQUE,
                            
                            CHECK (name REGEXP '^[a-z_]+$')
                        )
                    """, [List.TABLE_NAME, List.MAX_NAME_LENGTH, List.MAX_NAME_LENGTH])

                    p = queries.ParamHelper()

                    cursor.execute(f"""
                        CREATE TABLE {p(Attribute.TABLE_NAME)} (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            list_id INT NOT NULL,
                            name VARCHAR({p(List.MAX_NAME_LENGTH)}) NOT NULL,
                            display_name VARCHAR({p(List.MAX_NAME_LENGTH)}) NOT NULL,
                            sort_value INT NOT NULL,
                            alias JSON NOT NULL,
                            value_type INT NOT NULL,
                            value_collection BLOB,
                            min_value_slots INT NOT NULL,
                            max_value_slots INT NOT NULL,
                            unique_slots BOOL NOT NULL,
                            user_bound BOOL NOT NULL,
                            unique_in_list BOOL NOT NULL,

                            FOREIGN KEY (list_id) REFERENCES {p(List.TABLE_NAME)}(id)
                                ON DELETE RESTRICT
                            CHECK (name REGEXP '^[a-z_]+$'),
                            CHECK (display_name REGEXP '^[a-zA-Z ]+$'),
                            CHECK (NOT (user_bound AND unique_in_list))
                        )
                    """, p.params())
            except mariadb.Error:
                cursor.execute(f"DROP DATABASE `{self.database_name}`")
                raise fbe.TemporaryFeedbackError()
    
    def __hash__(self) -> int:
        return hash((self.id, hash(self.jumpedia)))
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, Community) and self.id == value.id and self.jumpedia == self.jumpedia
    
    def get_lists(self) -> list[List]:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ?
            """, [List.TABLE_NAME])

            result: list[list_module.ListTableT] = cursor.fetchall()

        lists: list[List] = []

        for l_data in result:
            lists.append(List(
                self,
                l_data['id'],
                l_data['name'],
                l_data['display_name'],
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