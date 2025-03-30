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

class Community:
    DEFAULT: 'Community' = ... # type: ignore

    def __hash__(self) -> int:
        ...
        

Community.DEFAULT = Community()