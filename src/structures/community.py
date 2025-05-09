from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Iterable, Self, TypedDict, Unpack
from threading import RLock
import discord as dc

import mariadb
from structures.ranks import UserRank
from utils import text
from database import queries
import discordtools.feedbackerrors as fbe
from typing import Optional as Opt
from structures.list import List, ListResultT
from structures import list as list_module
import jumpedia as jumpedia_

if TYPE_CHECKING:
    from structures.jumpedia import Jumpedia
    from structures.user import User, UserResultT

class CommunityResultT(TypedDict, total=True):
    id: int
    name: str
    display_name: str
    database_name: str  # virtual
    guild_ids: str

    
@dataclass(frozen=True, kw_only=True)
class Community:
    jumpedia: Jumpedia
    id: int
    guild_ids: frozenset[int]
    name: str
    display_name: str

    edit_lock: RLock = field(init=False, default_factory=RLock)

    @property
    def database_name(self) -> str:
        return f"{Community.DATABASE_PREFIX}{self.id}"
    
    MAX_NAME_LENGTH: ClassVar[Final[int]] = 64
    DATABASE_PREFIX: ClassVar[Final[str]] = f"{__name__}_"
    INVALID_ENDING: ClassVar[Final[str]] = __name__.lower()
    
    @classmethod
    def create(cls, jumpedia: Jumpedia, guild_ids: Iterable[int], bad_name: str) -> 'Community':
        with jumpedia.edit_lock:
            communities = jumpedia.get_communities()

            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True,
                Community.MAX_NAME_LENGTH,
                (c.name for c in communities)
            )

            if name.endswith(cls.INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out '{cls.INVALID_ENDING}' from the name as it is redundant!")
            
            database_name = f"{Community.DATABASE_PREFIX}{name}"
            guild_ids = frozenset(guild_ids)
            h = queries.ArgHelper()

            with queries.connected(jumpedia) as (conn, cursor):
                cursor.execute(f"""
                    INSERT INTO community
                    (name, display_name, database_name)
                    VALUES 
                    ({h|name}, {h|display_name}, {h|database_name})
                """, h.steal())

                community_id: int = cursor.lastrowid  # type: ignore

                cursor.execute(f"""
                    INSERT INTO guild
                    (id, community_id)
                    VALUES
                    {",".join(f"({h|guild_id}, {h|community_id})" for guild_id in guild_ids)}
                """, h.steal())
                
                obj = Community(
                    jumpedia=jumpedia,
                    id=cursor.lastrowid,  # type: ignore
                    guild_ids=guild_ids,
                    name=name,
                    display_name=display_name,

                )  

                # If anything goes wrong here, exception will cause it to 
                # rollback step above, where we add the community to meta table
                obj._init_database()

            return obj
        
    def _init_database(self) -> None:
        with self.jumpedia.edit_lock:
            # Create database
            with queries.connected(None) as (conn, cursor):
                cursor.execute(f"CREATE DATABASE `{self.database_name}`")
            
            # If anything goes wrong here, delete database and raise error
            try:
                # Create tables
                with queries.connected(self):
                    cursor.execute(f"""
                        CREATE TABLE list (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            name VARCHAR({List.MAX_NAME_LENGTH}) NOT NULL UNIQUE,
                            display_name VARCHAR({List.MAX_NAME_LENGTH}) NOT NULL UNIQUE,
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
            except mariadb.Error:
                cursor.execute(f"DROP DATABASE `{self.database_name}`")
                raise fbe.TemporaryFeedbackError()
    
    def __hash__(self) -> int:
        return hash((self.id, hash(self.jumpedia)))
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, Community) and self.id == value.id and self.jumpedia == self.jumpedia
    
    def _fetch_lists_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[ListResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM list
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[ListResultT] = cursor.fetchall()

        return result
    
    def _list_data_to_obj(self, data: ListResultT | None) -> List:
        if data is None:
            raise fbe.TemporaryFeedbackError("List does not exist!")
        
        return List(
            community=self,
            id=data['id'],
            name=data['name'],
            display_name=data['display_name']
        )
    
    def get_lists(self) -> list[List]:
        return [self._list_data_to_obj(data) for data in self._fetch_lists_from_table(None)]

    def get_list_by_id(self, id: int) -> List:
        data = self._fetch_lists_from_table(lambda h: f"id = {h|id}")
        return self._list_data_to_obj(data[0] if data else None)
    
    def get_list_by_name(self, name: str) -> List:
        name = text.norm(name)
        data = self._fetch_lists_from_table(lambda h: f"id = {h|name}")
        return self._list_data_to_obj(data[0] if data else None)
    
    def _fetch_users_from_table(self, where: Callable[[queries.ArgHelper], str] | None) -> list[UserResultT]:
        h = queries.ArgHelper()
        
        with queries.connected(self) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM user
                {f"WHERE {where(h)}" if where is not None else ""}
            """, h.steal())

            result: list[UserResultT] = cursor.fetchall()

        return result
    
    def _user_data_to_obj(self, data: UserResultT | None) -> User:
        if data is None:
            raise fbe.TemporaryFeedbackError("User does not exist!")
        
        return User(
            community=self,
            id=data['id'],
            user_rank=UserRank.get(data['power']),
            selected_list=(self.get_list_by_id(id) if (id := data['selected_list_id']) is not None else None)
        )
    
    def get_users(self) -> list[User]:
        return [self._user_data_to_obj(data) for data in self._fetch_users_from_table(None)]

    def get_user_by_id(self, id: int) -> User:
        data = self._fetch_users_from_table(lambda h: f"id = {h|id}")
        return self._user_data_to_obj(data[0] if data else None)
    
    def get_user_by_name(self, name: str) -> User:
        name = text.norm(name)
        data = self._fetch_users_from_table(lambda h: f"id = {h|name}")
        return self._user_data_to_obj(data[0] if data else None)
    