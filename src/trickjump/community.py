import discord as dc
from discordtools import errors, feedbackerrors as fbe
from typing import Iterable, Self
from utils.instance_manager import InstanceManager
from people.users import User
import string
from database import queries
import re
import threading

class Catalog:
    def __init__(self):
        ...
        
class Community:
    MANAGER: InstanceManager['Community', str | int] = InstanceManager(
        lambda instance: (instance.id, instance.name)
    )

    _ALLOWED_CHARS: set[str] = set(
        string.ascii_lowercase + string.digits + "_"
    )
    _WHITESPACE_PATTERN = re.compile(r'\s+')

    _DATABASE_SETUP_LOCK = threading.Lock()

    def __init__(self, id: int, name: str, guilds: Iterable[int], catalogues: Iterable[Catalog], owner: dc.User):
        self._id = id
        self._name = name
        self._guilds = frozenset(guilds)
        self._catalogues = frozenset(catalogues)
        self._owner = owner.id

    @classmethod
    def add(cls, initial_guild: dc.Guild, name: str, owner: dc.User) -> Self:
        name = re.sub(cls._WHITESPACE_PATTERN, ' ', name.strip())
        normalized_name = name.lower().replace(" ", "_").strip()

        if not name or not normalized_name:
            raise fbe.TemporaryFeedbackError
        
        if normalized_name[0].isdigit():
            raise fbe.TemporaryFeedbackError
        
        for char in normalized_name:
            if char not in cls._ALLOWED_CHARS:
                raise fbe.TemporaryFeedbackError
        
        with cls._DATABASE_SETUP_LOCK:
            with queries.connected(None) as (conn, cursor):
                cursor.execute(f"SHOW DATABASES LIKE '{normalized_name}'")

                if cursor.fetchone():
                    raise fbe.TemporaryFeedbackError
                
                cursor.execute(f"CREATE DATABASE {normalized_name}")
            
            # rollback not possible for database creation -> manual
            try:
                with queries.connected(normalized_name) as (conn, cursor):
                    cursor.execute("""
                        CREATE TABLE ? (
                            k VARCHAR(32) PRIMARY KEY,
                            v VARCHAR(2048)
                        )
                    """, (cls._METADATA_TABLE_NAME,))
                    #TODO create master table

                    cursor.execute(
                        "INSERT INTO ? (k, v) VALUES ('name', ?)",
                        (cls._METADATA_TABLE_NAME, name)
                    )

                instance: Self = cls(init)
            except Exception as e:
                try:
                    with queries.connected(None) as (conn, cursor):
                        cursor.execute(f"DROP DATABASE {normalized_name}")
                except Exception:
                    raise errors.CriticalError(e)
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def normalized_name(self) -> str:
        return self.name.lower().replace(' ', '_')
    
    @property
    def id(self) -> int:
        return self._id

