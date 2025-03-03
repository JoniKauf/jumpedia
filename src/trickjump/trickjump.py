from typing import TYPE_CHECKING, Annotated, Any, Generator, Sequence, overload, override, Optional as Opt
from dataclasses import dataclass
from database import queries
from trickjump import attributes as attrs
from people import person
from discordtools import feedbackerrors as fbe

type TrickjumpDataT = dict[str, Any]

if TYPE_CHECKING:
   from trickjump import catalog as cat
    
@dataclass(init=False, slots=True)
class Trickjump(attrs.AttrCollection):
    id:         attrs.Id
    name:       attrs.Name
    location:   attrs.AttrMultiValue[attrs.Location]
    difficulty: attrs.Difficulty
    type:       attrs.AttrMultiValue[attrs.Type]
    server:     attrs.Server
    finder:     attrs.AttrMultiValue[attrs.Finder]
    taser:      attrs.AttrMultiValue[attrs.Taser]
    prover:     attrs.AttrMultiValue[attrs.Prover]
    found_at:   attrs.FoundAt
    tased_at:   attrs.TasedAt
    proven_at:  attrs.ProvenAt
    link:       attrs.AttrMultiValue[attrs.Link]
    info:       attrs.Info
    tag:        attrs.AttrMultiValue[attrs.Tag]
    thumbnail:  attrs.Thumbnail

    def as_info(self) -> str:
        return "\n".join(f"{k}: {v}" for k, v in self.items())

    @classmethod
    def select_attrs(cls) -> str:
        return f"""
            SELECT {", ".join(cls.field_names())} FROM trickjump
        """
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, Trickjump):
            return False
        return self.id.value == value.id.value
    
    def __hash__(self) -> int:
        return hash(self.id.value)
    
    @classmethod
    def get_all(cls) -> 'cat.List':
        from trickjump import catalog as cat

        with queries.connected() as (conn, cursor):
            cursor.execute(cls.select_attrs())

            tjs_data: list[dict[str, Any]] = cursor.fetchall()

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