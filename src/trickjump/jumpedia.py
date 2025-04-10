from threading import RLock
from typing import Any, ClassVar, overload
from trickjump import community
from trickjump.parent import Parent
from trickjump.community import Community, CommunityTableT
from utils import metautils
from database import queries

# -> Jumpedia
#    -> Collection of Communities
#       -> Collection of Lists
#          -> Collection of Trickjumps

from dataclasses import dataclass, field

@dataclass(frozen=True)
class Jumpedia(Parent[Community], metaclass=metautils.Singleton):
    database_name: str

    edit_lock: RLock = field(init=False, default_factory=RLock)

    def _load_children(self) -> None:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ?
            """, [Community.META_TABLE_NAME])
            
            
            result: list[CommunityTableT] = cursor.fetchall()

        with self.edit_lock:
            self.children.clear()

            for c_data in result:
                community = Community(
                    c_data['id'],
                    c_data['name'],
                    c_data['display_name'],
                    c_data['database_name']
                )

                self.children.add(community)

JUMPEDIA = Jumpedia('meta')