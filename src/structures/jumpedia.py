from threading import RLock
from typing import Any, ClassVar, overload, Optional as Opt
from structures import community
from discordtools import feedbackerrors as fbe
from structures.attribute import Attribute
from structures.community import Community, CommunityTableT
from structures.list import List
from utils import metautils, text
from database import queries

# -> Jumpedia
#    -> Collection of Communities
#       -> Collection of Lists
#          -> Collection of Trickjumps

from dataclasses import dataclass, field

@dataclass(frozen=True, kw_only=False)
class Jumpedia(metaclass=metautils.Singleton):
    database_name: str
    edit_lock: RLock = field(init=False, default_factory=RLock)

    communities: set[Community] = field(init=False, default_factory=set)
    community_id_mapping: dict[int, Community] = field(init=False, default_factory=dict)
    community_name_mapping: dict[str, Community] = field(init=False, default_factory=dict)
    
    def _init_community_database(self, community: Community) -> None:
        with community.edit_lock:
            # Create database

            # Database either already exists or some other random error
            # happened. Anyways, this should not be able to happen!! If so
            # this makes it abort.
            with queries.connected(self) as (conn, cursor):
                cursor.execute(f"CREATE DATABASE `{self.database_name}`")
            
            # Create tables
            with queries.connected(self):
                cursor.execute("""
                    CREATE TABLE ? (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(?) NOT NULL UNIQUE,
                        display_name VARCHAR(?) NOT NULL UNIQUE,
                        
                        CHECK (name REGEXP '^[a-z_]+$')
                    )
                """, [List.TABLE_NAME, List.MAX_NAME_LENGTH, List.MAX_NAME_LENGTH])

                # TODO: Compete attribute table
                cursor.execute("""
                    CREATE TABLE ? (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        ? INT NOT NULL
                    )
                """, [Attribute.TABLE_NAME, f'{List.TABLE_NAME}_id'])

                id: int
                name: str
                display_name: str
                alias: list[str]
                value_type: int
                value_collection: None | list[CollectionItemT[T]] | CollectionTreeT[T]
                min_value_slots: int
                max_value_slots: int
                unique_slots: bool
                user_bound: bool
                unique_in_list: bool
    
    def _add_to_community_collection(self, community: Community):
        with self.edit_lock:
            self.communities.add(community)
            self.community_id_mapping[community.id] = community
            self.community_name_mapping[community.name] = community

    def reload_communities(self) -> None:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ?
            """, [Community.META_TABLE_NAME])
            
            result: list[CommunityTableT] = cursor.fetchall()

        with self.edit_lock:
            self.communities.clear()
            self.community_id_mapping.clear()
            self.community_name_mapping.clear()

            for c_data in result:
                self._add_to_community_collection(Community(
                    c_data['id'],
                    c_data['name'],
                    c_data['display_name'],
                    c_data['database_name'],
                    self
                ))

    def create_community(self, bad_name: str) -> Community:
        with self.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True, 
                self.community_name_mapping
            )
            
            # They should be the same name because we lower and not casefold,
            # but just to make sure
            if any(len(n) > Community.MAX_NAME_LENGTH for n in (name, display_name)):
                raise fbe.TemporaryFeedbackError("Too long name, max is 50 chars")
            
            if name.endswith(Community.META_TABLE_NAME):
                raise fbe.TemporaryFeedbackError(f"Please leave out '{Community.META_TABLE_NAME}' from you {Community.META_TABLE_NAME}'s name, as it is redundant!")
            
            database_name = f"{Community.DATABASE_PREFIX}{name}"

            with queries.connected(self) as (conn, cursor):
                cursor.execute(f"""
                    SELECT *
                    FROM ?
                    WHERE name = ?
                """, [Community.META_TABLE_NAME, name])

                result_opt: Opt[CommunityTableT] = cursor.fetchone()

                if result_opt:
                    raise fbe.TemporaryFeedbackError(f"{Community.META_TABLE_NAME.title()} with that name exists already")
                
                cursor.execute("""
                    INSERT INTO ?
                    (name, display_name, database_name)
                    VALUES (?, ?, ?)
                """, [Community.META_TABLE_NAME, name, display_name, database_name])
                
                # To get id
                cursor.execute("""
                    SELECT * FROM ? WHERE name = ?
                """, [Community.META_TABLE_NAME, name])

                result: CommunityTableT = cursor.fetchone()
                
                obj = Community(
                    result['id'],
                    result['name'],
                    result['display_name'],
                    result['database_name'],
                    self
                )  

                # If anything goes wrong here, exception will cause it to 
                # rollback step above, where we add the community to meta table
                self._init_community_database(obj)
            
            self._add_to_community_collection(obj)
            return obj
    
    def get_community_by_id(self, id: int) -> Community:
        try:
            return self.community_id_mapping[id]
        except KeyError as e:
            raise LookupError(*e.args)
        
    def get_community_by_name(self, name: str) -> Community:
        try:
            return self.community_name_mapping[name]
        except KeyError as e:
            raise LookupError(*e.args)
        
    

JUMPEDIA = Jumpedia('meta')