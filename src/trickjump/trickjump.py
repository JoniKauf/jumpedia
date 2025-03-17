from typing import TYPE_CHECKING, Annotated, Any, Generator, Sequence, overload, override, Optional as Opt
from dataclasses import dataclass
from database import queries
from trickjump import attributes as attrs
from people import person
from discordtools import feedbackerrors as fbe

class Trickjump(dict[str, Any]):
    def as_info(self) -> str:
        return "\n".join(f"{k}: {v}" for k, v in self.items())
    
    @classmethod
    def get_all(cls):
        all_attrs = attrs.get_all('Jumpedia')

        with queries.connected() as (conn, cursor):
            cursor.execute("SELECT * FROM trickjump")

            result: list = cursor.fetchall()

        for data in result:
            pass
            

        return cat.List(
            Trickjump(tj, required=True, lower=False) 
            for tj in tjs_data
        )
    
    @classmethod
    def get_all_names(cls) -> list[str]:
        with queries.connected() as (conn, cursor):
            cursor.execute("""SELECT name FROM trickjump""")

            result: list[TrickjumpDataT] = cursor.fetchall()

        return [tj['name'] for tj in result]
    
    @classmethod
    def get_by_name(cls, name: str) -> 'Trickjump':
        with queries.connected() as (conn, cursor):
            cursor.execute(
                f"{cls.select_attrs()} WHERE name = ? LIMIT 1", 
                (name,)
            )

            result: TrickjumpDataT = cursor.fetchone()

        if result is None:
            raise fbe.NotAJump(name)
        
        return cls(result)
        
    def get_contributor_line(self) -> str:
        def join_grammatically(elems: Sequence[str]):
            if len(elems) < 2:
                return ''.join(elems)
            return ', '.join((*elems[:-1], f" & {elems[-1]}"))
        
        contributors: Generator[attrs.AttrPerson | attrs.AttrMultiValue[attrs.AttrPerson]] = (
            v for v in self.values(lambda _, val: issubclass(val.value_cls, attrs.AttrPerson))
        )  # type: ignore

        action_to_people: dict[str, tuple[person.Person, ...]] = {
            person.value_cls.ACTION: person.unpacked for person in contributors
        }

        people_to_action: dict[tuple[str, ...], list[str]] = {}

        for title, value in action_to_people.items():
            people_to_action.setdefault(
                tuple(person.name for person in value), []
            ).append(title)

        # Remove empty values
        people_to_action.pop((), None)

        return ', '.join(
            f"{join_grammatically(titles)} by {join_grammatically(value)}"
            for value, titles in people_to_action.items()
        )