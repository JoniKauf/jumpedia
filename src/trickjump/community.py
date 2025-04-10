# import discord as dc
# from discordtools import errors, feedbackerrors as fbe
# from typing import Iterable, Self
# from utils.instance_manager import InstanceManager
# from people.user import User
# import string
# from database import queries
# import re
# import threading

# class Catalog:
#     def __init__(self):
#         ...
        
# class Community:
#     MANAGER: InstanceManager['Community', str | int] = InstanceManager(
#         lambda instance: (instance.id, instance.name)
#     )

#     _ALLOWED_CHARS: set[str] = set(
#         string.ascii_lowercase + string.digits + "_"
#     )
#     _WHITESPACE_PATTERN = re.compile(r'\s+')

#     _DATABASE_SETUP_LOCK = threading.Lock()

#     def __init__(self, id: int, name: str, guilds: Iterable[int], catalogues: Iterable[Catalog], owner: dc.User):
#         self._id = id
#         self._name = name
#         self._guilds = frozenset(guilds)
#         self._catalogues = frozenset(catalogues)
#         self._owner = owner.id

#     @classmethod
#     def add(cls, initial_guild: dc.Guild, name: str, owner: dc.User) -> Self:
#         name = re.sub(cls._WHITESPACE_PATTERN, ' ', name.strip())

#         if len(name) < 3:
#             raise fbe.TemporaryFeedbackError
        
#         for char in name:
#             if char not in cls._ALLOWED_CHARS:
#                 raise fbe.TemporaryFeedbackError
        
#         with cls._DATABASE_SETUP_LOCK:
#             with queries.connected('master') as (conn, cursor):
#                 cursor.execute("C")
    
#     @property
#     def name(self) -> str:
#         return self._name
    
#     @property
#     def normalized_name(self) -> str:
#         return self.name.lower().replace(' ', '_')
    
#     @property
#     def id(self) -> int:
#         return self._id

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import ClassVar, Self, TypedDict, Unpack
from threading import RLock

import mariadb
from trickjump.parent import Lookupable
from utils import text
from database import queries
import discordtools.feedbackerrors as fbe
from typing import Optional as Opt
from trickjump.list import List

class CommunityTableT(TypedDict, total=True):
    id: int
    name: str
    display_name: str
    database_name: str

@dataclass(frozen=True)
class Community(Lookupable):
    display_name: str
    database_name: str
    lists: set[List] = field(init=False, default_factory=set)

    DATABASE_PREFIX: ClassVar[str] = "c_"
    META_TABLE_NAME: ClassVar[str] = "community"

    MAX_NAME_LENGTH: ClassVar[int] = 50

    _EDIT_LOCK: ClassVar[RLock] = RLock()
    _LOOKUP: ClassVar[MappingProxyType[str, 'Community']] = MappingProxyType({})

    def __hash__(self) -> int:
        return hash(self.id)

    @classmethod
    def create(cls, bad_name: str) -> Self:
        with Community._EDIT_LOCK:
            display_name = text.fix_whitespace(bad_name.strip(), ' ')
            name = Community._normalize_name(bad_name)

            if bad_chars := text.invalid_identifier_chars(bad_name):
                raise fbe.TemporaryFeedbackError(bad_chars)
            
            if any(len(n) > Community.MAX_NAME_LENGTH for n in (bad_name, display_name)):
                raise fbe.TemporaryFeedbackError("Too long name")
            
            if bad_name.endswith("community"):
                raise fbe.TemporaryFeedbackError("Please leave out 'community' from you community's name, as it is redundant!")
            
            database_name = f"{Community.DATABASE_PREFIX}{name}"

            with queries.connected(queries.MetaDatabase) as (conn, cursor):
                cursor.execute(f"""
                    SELECT *
                    FROM ?
                    WHERE name = ?
                """, (Community.META_TABLE_NAME, database_name,))

                result_opt: Opt[CommunityTableT] = cursor.fetchone()

                if result_opt:
                    raise fbe.TemporaryFeedbackError("Community with that name exists already")
                
                cursor.execute("""
                    INSERT INTO ?
                    (name, display_name, database_name)
                    VALUES (?, ?, ?)
                """, (Community.META_TABLE_NAME, name, display_name, database_name))

                cursor.execute("""
                    SELECT * FROM ? WHERE name = ?
                """, Community.META_TABLE_NAME, name)

                result: CommunityTableT = cursor.fetchone()
                obj = cls(**result)  # type: ignore

                # Must be last thing to occur in database, because rolling
                # meta things back is not possible
                cursor.execute(f"CREATE DATABASE `{database_name}`")

            with queries.connected(obj) as (conn, cursor):
                cursor.execute("""
                    CREATE TABLE ? (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR()
                    )
                """, (List.TABLE_NAME,))

            Community.reload_communities()
            return obj

    @classmethod
    def reload_communities(cls) -> None:
        with cls._EDIT_LOCK:
            with queries.connected(queries.MetaDatabase) as (conn, cursor):
                cursor.execute(f"""
                    SELECT * FROM ?
                """, (Community.META_TABLE_NAME,))

                result: list[CommunityTableT] = cursor.fetchall()

            cls._LOOKUP = MappingProxyType({
                c['name']: cls(**c) for c in result  # type: ignore
            })
    
    @classmethod
    def _normalize_name(cls, bad_name: str) -> str:
        return text.fix_whitespace(bad_name.strip(), '_').lower()
    
    @classmethod
    def get(cls, bad_name: str) -> 'Community':
        return cls._LOOKUP[cls._normalize_name(bad_name)]
    
    def delete(self) -> bool:
        """Delete the community entirely.
        
        Returns True if it was successful, otherwise 
        """

        # This order does secure data integrity if anything goes wrong
        try:
            with queries.connected(queries.MetaDatabase) as (conn, cursor):
                cursor.execute("""
                    DELETE FROM ?
                    WHERE id = ?
                """, (Community.META_TABLE_NAME, self.id))

                with queries.connected(self) as (conn, cursor):
                    cursor.execute(f"""
                        DROP DATABASE `{self.database_name}`
                    """)
        except mariadb.Error:
            return False
        
        Community.reload_communities()

        return True