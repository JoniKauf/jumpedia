import enum
import re

import mariadb
from database import queries
from typing import Any, NamedTuple, Optional as Opt, Self

from discordtools import errors, feedbackerrors as fbe
from people import ranks

import discord as dc

_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')

def user_id_to_int(user_id: str | int) -> int:
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

    @classmethod
    def get(cls, user: str | int | 'User') -> 'User':
        if isinstance(user, User):
            return user
        
        if isinstance(user, (str, int)):
            id = user_id_to_int(user)
        elif not isinstance(user, int):
            raise TypeError("expected int | str for user")
        
        with queries.connected(final_commit=False) as (conn, cursor):
            cursor.execute("""
               SELECT * FROM user WHERE user.id = ?        
            """, [id])

            result: Opt[dict[str, Any]] = cursor.fetchone()

            if result is None:
                raise fbe.PersonDoesNotExist(user)

        return cls(
            id=result['id'], 
            name=result['name'],
            rank=ranks.UserRank.get(result['rank_power']),
            person_id=result['person_id'],
        )

    def save(self, overwrite: bool) -> None:
        insert_into: str = (
            "INSERT IGNORE INTO" if overwrite else "INSERT INTO"
        )
        
        try:
            with queries.connected(final_commit=True) as (conn, cursor):
                cursor.execute(f"""
                    {insert_into} user (id, name, rank_power, person_id) VALUES
                    (?, ?, ?, ?)
                """, (self.id, self.name, self.rank.power, self.person_id))
        except mariadb.DatabaseError:
            return

