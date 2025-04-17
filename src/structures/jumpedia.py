from threading import RLock
from typing import Any, ClassVar, overload, Optional as Opt

import mariadb
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
    database_name: str = field(init=False, default='meta')
    edit_lock: RLock = field(init=False, default_factory=RLock)
    
    def __post_init__(self) -> None:
        with queries.connected(self) as (conn, cursor):
            try:
                cursor.execute(f"""
                    CREATE DATABASE `{self.database_name}`
                """)
            except mariadb.Error:
                return

            cursor.execute("""
                CREATE TABLE ? (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(?) UNIQUE,
                    display_name VARCHAR(?) UNIQUE,
                    database_name VARCHAR(?) UNIQUE
                )
            """, [Community.META_TABLE_NAME, *([Community.MAX_NAME_LENGTH] * 3)])

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

    def create_community(self, bad_name: str) -> Community:
        with self.edit_lock:
            name, display_name = text.create_name_and_display_name(
                bad_name, 
                True,
                Community.MAX_NAME_LENGTH,
                (c.name for c in self.get_communities())
            )
            
            INVALID_ENDING = Community.__name__.lower()

            if name.endswith(INVALID_ENDING):
                raise fbe.TemporaryFeedbackError(f"Please leave out '{INVALID_ENDING}' from the name as it is redundant!")
            
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
                
                obj = Community(
                    self,
                    cursor.lastrowid,  # type: ignore
                    name,
                    display_name,
                    database_name
                )  

                # If anything goes wrong here, exception will cause it to 
                # rollback step above, where we add the community to meta table
                self._init_community_database(obj)

            return obj

    def get_communities(self) -> list[Community]:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ?
            """, [Community.META_TABLE_NAME])
            
            result: list[CommunityTableT] = cursor.fetchall()

        communities: list[Community] = []

        for c_data in result:
            communities.append(Community(
                self,
                c_data['id'],
                c_data['name'],
                c_data['display_name'],
                c_data['database_name'],
            ))

        return communities
    
    def _get_community(self, data: Opt[community.CommunityTableT]) -> Community:
        if data is None:
            raise fbe.TemporaryFeedbackError("Community does not exist!")
        
        return Community(
            jumpedia=self,
            id=data['id'],
            name=data['name'],
            display_name=data['display_name'],
            database_name=data['database_name']
        )
    
    def get_community_by_id(self, id: int) -> Community:
        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ? WHERE id = ?
            """, [Community.META_TABLE_NAME, id])

            result: Opt[community.CommunityTableT] = cursor.fetchone()

        return self._get_community(result)
        
    def get_community_by_name(self, name: str) -> Community:
        name = text.norm(name)

        with queries.connected(self) as (conn, cursor):
            cursor.execute("""
                SELECT * FROM ? WHERE name = ?
            """, [Community.META_TABLE_NAME, name])

            result: Opt[community.CommunityTableT] = cursor.fetchone()

        return self._get_community(result)