import enum
import re

import mariadb
from database import queries
from typing import Any, NamedTuple, Optional as Opt, Self

from discordtools import errors, feedbackerrors as fbe
from people import ranks

import discord as dc

_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')

type UserT = int | str | 'User' | dc.User | dc.Member

class User:
    def __init__(
        self, 
        id: int, 
        name: str, 
        rank: ranks.UserRank, 
        person_id: Opt[int] = None
    ) -> None:
        self.id = id
        self.name = name
        self.rank = rank
        self.person_id = person_id
    
    def __str__(self) -> str:
        return self.name
    
    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"({self.id}, {self.name}, {self.rank}, {self.person_id})"
        )
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, User):
            return False
        return self.id == value.id
    
    def __ne__(self, value: object) -> bool:
        return not (self.__eq__(value)) 
            
    @classmethod
    def get(
        cls, 
        id: str | int, 
        *, 
        name: Opt[str] = None, 
        rank: ranks.UserRank = ranks.USER_RANKS.USER,
        person_id: Opt[int] = None
    ) -> 'User':
        """If name is specified, it saves/overwrites the user."""

        if not isinstance(id, (str, int)):
            raise TypeError("expected int | str for user")
        
        id = cls._user_id_to_int(id)
        
        with queries.connected() as (conn, cursor):
            cursor.execute("""
               SELECT name, rank_power, person_id FROM user WHERE user.id = ?        
            """, [id])

            result: Opt[dict[str, Any]] = cursor.fetchone()
            
        if result is None:
            if not name:
                raise fbe.PersonDoesNotExist(id)

            user_obj = cls(
                id=id,
                name=name,
                rank=rank,
                person_id=person_id
            )

            user_obj.save(overwrite=True)
            return user_obj
        
        # here result: dict[str, Any] (not None)
        # Keep best rank of new and old data
        if (power := result['rank_power']) > rank.power:
            rank = ranks.UserRank.get(power)

        user_obj = cls(
            id=id, 
            name=result['name'], # prefer old name because it could be custom
            rank=rank, 
            person_id=person_id or result['person_id'],  # overwrite person_id
        )

        if name:
            user_obj.save(overwrite=True)

        return user_obj
    

    @staticmethod
    def _user_id_to_int(user_id: str | int) -> int:
        if isinstance(user_id, int):
            if user_id < 0:
                raise fbe.InvalidUserFormat(user_id)
            
            return user_id
        
        if user_id.isdigit():
            id = int(user_id)
        elif match := re.match(_USER_MENTION_PATTERN, user_id.strip()):
            id = int(match.group(1) or match.group(2))
        else:
            raise fbe.InvalidUserFormat(user_id)
        
        return id

    @staticmethod
    def _get_id(user: UserT) -> int:
        if isinstance(user, (str, int)):
            return User._user_id_to_int(user)
        elif isinstance(user, (User, dc.User, dc.Member)):
            return user.id
        
        raise TypeError()
        
    @classmethod
    def get_if_permitted(
        cls,
        ia: dc.Interaction,
        other_user_identifier: UserT,
        min_user_rank: ranks.UserRank = ranks.USER_RANKS.JONIKAUF,
        min_server_rank: ranks.ServerRank = ranks.SERVER_RANKS.MEMBER
    ) -> tuple['User', 'User']:
        """Return: tuple[executing_user, other_user],"""
        server_rank_this_user = ranks.get_server_rank(ia.user)

        if server_rank_this_user < min_server_rank:
            raise fbe.NoPermissionForOtherUsers(
                None,
                (server_rank_this_user, min_server_rank)
            )
        
        other_user_id = cls._get_id(other_user_identifier)

        this_user: Opt[User] = User.get(
            id=ia.user.id,
            name=ia.user.global_name or ia.user.name
        )

        # Allow to get info about oneself
        if other_user_id == ia.user.id:
            return this_user, this_user
        
        if this_user.rank < min_user_rank:
            raise fbe.NoPermissionForOtherUsers(
                (this_user.rank, min_user_rank)
            )
        
        other_user = User.get(other_user_id)

        return this_user, other_user
    
        
    def save(self, overwrite: bool) -> None:
        insert_into: str = (
            "INSERT IGNORE INTO" if overwrite else "INSERT INTO"
        )
        
        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                {insert_into} user 
                (id, name, rank_power, person_id) 
                VALUES
                (?, ?, ?, ?)
            """, (self.id, self.name, self.rank.power, self.person_id))

            conn.commit()
