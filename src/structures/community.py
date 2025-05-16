from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Iterable, Self, TypedDict, Unpack
from threading import RLock
import discord as dc

import mariadb
from utils import text
from database import queries
import discordtools.feedbackerrors as fbe
from typing import Optional as Opt

from structures.list import List
from structures.user import User
from structures.ranks import UserRank
from structures.task import Task

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia


class UserResultT(TypedDict):
    id: int
    power: int
    selected_list_id: int | None

class ListResultT(TypedDict):
    id: int
    name: str
    community_id: int
 
@dataclass(frozen=True, kw_only=True)
class Community:
    MAX_NAME_LENGTH: ClassVar[int] = 64
    MAX_LISTS: ClassVar[int] = 1
    DATABASE_PREFIX: ClassVar[str] = "community_".lower()
    INVALID_ENDING: ClassVar[str] = "community".lower()

    jumpedia: 'Jumpedia'
    id: int
    name: str
    default_selected_list_id: int | None
    guild_ids: frozenset[int]

    edit_lock: RLock = field(init=False, default_factory=RLock)

    @property
    def identity(self) -> tuple[int, ...]:
        return (self.id,) + self.jumpedia.identity
    
    @property
    def database_name(self) -> str:
        return f"{Community.DATABASE_PREFIX}{self.id}"

    def __hash__(self) -> int:
        return hash(self.identity)
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.identity == value.identity

    @classmethod
    def create(cls, jumpedia: 'Jumpedia', guild_ids: Iterable[int], bad_name: str) -> 'Community':
        with jumpedia.edit_lock:
            communities = jumpedia.get_communities()

            name = text.validate_and_sanitize_name(
                bad_name,
                cls.MAX_NAME_LENGTH,
                (c.name for c in communities)
            )

            if text.norm_syn(name).endswith(cls.INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out '{cls.INVALID_ENDING}' from the name as it is redundant!")
            
            guild_ids = frozenset(guild_ids)
            h = queries.ArgHelper()

            with queries.connected(jumpedia) as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO community (
                        name
                    )
                    VALUES (
                        {h|name}
                    )
                """, h.steal())

                id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO guild (
                        id, 
                        community_id
                    )
                    VALUES
                    {",".join(f"({h|guild_id}, {h|id})" for guild_id in guild_ids)}
                """, h.steal())
                
                obj = cls(
                    jumpedia=jumpedia,
                    id=id,
                    guild_ids=guild_ids,
                    default_selected_list_id=None,
                    name=name
                )  

                # If anything goes wrong here, exception will cause it to 
                # rollback step above, where we add the community to meta table
                obj._init_database()

                List.create(obj, 'Main')

                return obj
        
    def _init_database(self) -> None:
        # Lock should be obtained here already

        from structures.attribute import TaskAttribute, UserAttribute

        with queries.connected(None) as (none_conn, none_cursor):
            # Create database
            none_cursor.execute(f"""
                CREATE DATABASE `{self.database_name}`
                    CHARACTER SET = utf8mb4
                    COLLATE = utf8mb4_unicode_ci
            """)
        
            with queries.connected(self) as (conn, cursor):
                # If anything goes wrong here, delete database and raise error
                try:
                    # Create tables
                    cursor.execute(f"""
                        CREATE TABLE list (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR({List.MAX_NAME_LENGTH}) NOT NULL UNIQUE
                        )
                    """)

                    cursor.execute("""
                        CREATE TABLE user (
                            id BIGINT UNSIGNED PRIMARY KEY,
                            power INT NOT NULL,
                            selected_list_id INT,
                                
                            FOREIGN KEY (selected_list_id) 
                                REFERENCES list(id) 
                                ON DELETE SET NULL
                        )
                    """)

                    cursor.execute(f"""
                        CREATE TABLE task_attribute (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            list_id INT NOT NULL,
                            name VARCHAR({TaskAttribute.MAX_SYN_LEN}) UNIQUE NOT NULL,
                            value_type INT NOT NULL,
                            `index` INT NOT NULL UNIQUE,
                            collection BLOB NOT NULL,
                            min_slots INT NOT NULL,
                            max_slots INT NOT NULL,
                            unique_slots BOOL NOT NULL,
                            unique_value_per_list BOOL NOT NULL,

                            FOREIGN KEY (list_id)
                                REFERENCES list(id)
                                ON DELETE CASCADE
                        )
                    """)

                    cursor.execute(f"""
                        CREATE TABLE user_attribute (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            list_id INT NOT NULL,
                            name VARCHAR({UserAttribute.MAX_SYN_LEN}) UNIQUE NOT NULL,
                            `index` INT NOT NULL UNIQUE,
                            value_type INT NOT NULL,
                            collection BLOB NOT NULL,
                            min_slots INT NOT NULL,
                            max_slots INT NOT NULL,
                            unique_slots BOOL NOT NULL,

                            FOREIGN KEY (list_id)
                                REFERENCES list(id)
                                ON DELETE CASCADE
                        )
                    """)

                    cursor.execute(f"""
                        CREATE TABLE task_attribute_alias (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            task_attribute_id INT NOT NULL,
                            alias VARCHAR({TaskAttribute.MAX_SYN_LEN}) UNIQUE NOT NULL,

                            FOREIGN KEY (task_attribute_id)
                                REFERENCES task_attribute(id)
                                ON DELETE CASCADE
                        )
                    """)

                    cursor.execute(f"""
                        CREATE TABLE user_attribute_alias (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            user_attribute_id INT NOT NULL,
                            alias VARCHAR({UserAttribute.MAX_SYN_LEN}) UNIQUE NOT NULL,

                            FOREIGN KEY (user_attribute_id)
                                REFERENCES user_attribute(id)
                                ON DELETE CASCADE
                        )
                    """)

                    cursor.execute(f"""
                        CREATE TABLE task (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            list_id INT NOT NULL,
                            name VARCHAR({Task.MAX_SYN_LEN}),
                                
                            FOREIGN KEY (list_id)
                                REFERENCES list(id)
                                ON DELETE CASCADE
                        )
                    """)

                    cursor.execute(f"""
                        CREATE TABLE task_alias (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            task_id INT NOT NULL,
                            alias VARCHAR({Task.MAX_SYN_LEN}),

                            FOREIGN KEY (task_id)
                                REFERENCES task(id)
                                ON DELETE CASCADE
                        )
                    """)

                    cursor.execute(f"""
                        CREATE TABLE task_attribute_value (
                            task_id INT NOT NULL,
                            task_attribute_id INT NOT NULL,
                            value BLOB NOT NULL,

                            PRIMARY KEY (task_id, task_attribute_id),

                            FOREIGN KEY (task_id)
                                REFERENCES task(id)
                                ON DELETE CASCADE,
                            FOREIGN KEY (task_attribute_id)
                                REFERENCES task_attribute(id)
                                ON DELETE CASCADE
                        )
                    """)

                    cursor.execute(f"""
                        CREATE TABLE task_user_attribute_value (
                            task_id INT NOT NULL,
                            user_id BIGINT UNSIGNED NOT NULL,
                            user_attribute_id INT NOT NULL,
                            value BLOB NOT NULL,

                            PRIMARY KEY (task_id, user_id, user_attribute_id),

                            FOREIGN KEY (task_id)
                                REFERENCES task(id)
                                ON DELETE CASCADE,
                            FOREIGN KEY (user_attribute_id)
                                REFERENCES user_attribute(id)
                                ON DELETE CASCADE,
                            FOREIGN KEY (user_id)
                                REFERENCES user(id)
                                ON DELETE CASCADE
                        )
                    """)
                except mariadb.Error as e:
                    none_cursor.execute(f"DROP DATABASE `{self.database_name}`")
                    raise e
    
    def _fetch_from_list_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[ListResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM list
                {f"WHERE {where(h)}" if where is not None else ""}
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
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM user
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list['UserResultT'] = cursor.fetchall()

        return result
    
    def _user_data_to_obj(self, data: UserResultT) -> 'User':  
        return User(
            community=self,
            id=data['id'],
            user_rank=UserRank.get(data['power']),
            selected_list=self.get_default_selected_list()
        )
    
    def get_users(self, where: Callable[[queries.ArgHelper], str] | None = None) -> list['User']:
        return [
            self._user_data_to_obj(data) 
            for data in self._fetch_from_user_table(where)
        ]

    def get_user_by_id(self, id: int) -> 'User | None':
        data = self._fetch_from_user_table(lambda h: f"id = {h|id}")
        return self._user_data_to_obj(data[0]) if data else None
    
    def get_user_by_name(self, name: str) -> 'User | None':
        name = text.norm(name)
        data = self._fetch_from_user_table(lambda h: f"name = {h|name}")
        return self._user_data_to_obj(data[0]) if data else None