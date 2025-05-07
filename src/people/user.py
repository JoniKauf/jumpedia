from dataclasses import dataclass, field
import enum
import re

import mariadb
from database import queries
from typing import Any, ClassVar, Final, NamedTuple, Self, TypedDict

from discordtools import errors, feedbackerrors as fbe

import discord as dc

from people.ranks import UserRank
from structures.context import Context
from structures.list import List

_USER_MENTION_PATTERN: re.Pattern = re.compile(r'^<@!?(\d+)>$|^<@&(\d+)>$')

type UserIdentifierT = int | str | 'User' | dc.User | dc.Member

class UserTableT(TypedDict):
    id: int
    power: int
    selected_list_id: int | None

@dataclass()
class User:
    TABLE_NAME: ClassVar[str] = __name__.lower()
    MAX_NAME_LENGTH: ClassVar[int] = 32

    id: int
    power: int
    selected_list: List | None
    
    def __eq__(self, value: object) -> bool: 
        return isinstance(value, User) and self.id == value.id
    
    @classmethod
    def get(cls, ctx: Context) -> 'User':
        h = queries.ArgHelper()

        id, power, selected_list_id = (ctx.interaction.user.id, UserRank.USER.power, None)

        with queries.connected(ctx.community) as (conn, cursor):
            try:
                cursor.execute(f"""
                    INSERT INTO {h|cls.TABLE_NAME}
                    (id, power, selected_list_id)
                    VALUES
                    ({h|id}, {h|power}, {h|selected_list_id})
                """, h.steal())
            except mariadb.Error:
                cursor.execute(f"""
                    SELECT *
                    FROM {h|cls.TABLE_NAME}
                """)

                result: UserTableT = cursor.fetchone()
                id, power, selected_list_id = (result['id'], result['power'], result['selected_list_id'])

        return User(
            id=id,
            power=power,
            selected_list=List.get  # TODO
        )
    
    @classmethod
    def get_other(cls, ctx: Context, id: UserIdentifierT) -> 'User':
        id = cls._get_id(id)
        h = queries.ArgHelper()
        
        with queries.connected(ctx.community) as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM {h|cls.TABLE_NAME} 
                WHERE id = {h|id}        
            """, h.steal())

            result: UserTableT | None = cursor.fetchone()
        
        if result is None:
            raise fbe.PersonDoesNotExist()
        
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
    def _get_id(user: UserIdentifierT) -> int:
        if isinstance(user, (str, int)):
            return User._user_id_to_int(user)
        elif isinstance(user, (User, dc.User, dc.Member)):
            return user.id
        
        raise TypeError()
        
    @classmethod
    def get_if_permitted(
        cls,
        ia: dc.Interaction,
        other_user_identifier: UserIdentifierT,
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

        this_user: Opt[User] = User.get_other(
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
        
        other_user = User.get_other(other_user_id)

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
