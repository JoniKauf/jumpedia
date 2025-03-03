import json
from typing import ClassVar, Self
from discordtools import feedbackerrors as fbe
from database import queries


class Person:
    LOOKUP: ClassVar[dict[str | int, 'Person']] = {}
    MAX_PERSON_NAME_LEN = 32

    def __init__(self, id: int, name: str) -> None:
        if len(name) > self.__class__.MAX_PERSON_NAME_LEN:
            raise fbe.TemporaryFeedbackError()
        
        self.id: int = id
        self.name: str = name
        self._add()
    
    def __str__(self) -> str:
        return str(self.name)
    
    def __hash__(self) -> int:
        return hash(self.id)
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Person):
            return False
        
        return self.id == value.id
    
    def _add(self):
        self.__class__.LOOKUP[self.name.casefold()] = self
        self.__class__.LOOKUP[self.id] = self

    @classmethod
    def get(cls, value: str | int) -> 'Person':
        try:
            return cls.LOOKUP[
                value.casefold() if isinstance(value, str) else value
            ]
        except KeyError:
            raise fbe.PersonDoesNotExist(value)


# with queries.connected() as (conn, cursor):
#     cursor.execute("SELECT finder, taser, prover FROM trickjump")

#     all: set[str] = set()

#     rows: list[dict[str, list[str] | None]] = cursor.fetchall()

#     for row in rows:
#         for person in row.values():
#             if person is not None:
#                 all = all.union(person)

#     for i, person in enumerate(all, start=1):
#         Person(i, person)