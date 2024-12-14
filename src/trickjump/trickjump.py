from typing import Annotated, Any, Generator, Sequence, overload, override
from dataclasses import dataclass

from trickjump import attributes as attrs
from trickjump.attributes import AttributeCollection
from users import person


type TrickjumpDataT = dict[str, Any]

@dataclass(init=False, slots=True)
class Trickjump(AttributeCollection):
    name:       Annotated[attrs.Name, attrs.AttrMetadata(True)]
    location:   Annotated[attrs.AttrMultiValue[attrs.Location], attrs.AttrMetadata(True)]
    difficulty: Annotated[attrs.Difficulty, attrs.AttrMetadata(True)]
    type:       Annotated[attrs.AttrMultiValue[attrs.Type], attrs.AttrMetadata(True)]
    server:     Annotated[attrs.Server, attrs.AttrMetadata(True)]
    finder:     Annotated[attrs.AttrMultiValue[attrs.Finder], attrs.AttrMetadata(True)]
    taser:      Annotated[attrs.AttrMultiValue[attrs.Taser], attrs.AttrMetadata(True)]
    prover:     Annotated[attrs.AttrMultiValue[attrs.Prover], attrs.AttrMetadata(True)]
    found_at:   Annotated[attrs.FoundAt, attrs.AttrMetadata(True)]
    tased_at:   Annotated[attrs.TasedAt, attrs.AttrMetadata(True)]
    proven_at:  Annotated[attrs.ProvenAt, attrs.AttrMetadata(True)]
    link:       Annotated[attrs.AttrMultiValue[attrs.Link], attrs.AttrMetadata(True)]
    info:       Annotated[attrs.Info, attrs.AttrMetadata(True)]
    tag:        Annotated[attrs.AttrMultiValue[attrs.Tag], attrs.AttrMetadata(True)]
    thumbnail:  Annotated[attrs.Thumbnail, attrs.AttrMetadata(True)]

    def as_info(self) -> str:
        return "\n".join(f"{elem.NAME}: {elem.value}" for elem in self.__dict__.values())

    def get_contributor_line(self) -> str:
        def join_grammatically(elems: Sequence[str]):
            if len(elems) < 2:
                return ''.join(elems)
            return ', '.join((*elems[:-1], f" & {elems[-1]}"))
        
        contributors: Generator[attrs.AttrPerson | attrs.AttrMultiValue[attrs.AttrPerson]] = (
            v for v in self.values(lambda attr: issubclass(attr.value_cls, attrs.AttrPerson))
        )  # type: ignore

        action_to_people: dict[str, tuple[person.Person, ...]] = {
            person.value_cls.ACTION: person.unpacked for person in contributors
        }

        people_to_action: dict[tuple[str, ...], list[str]] = {}

        for title, value in action_to_people.items():
            people_to_action.setdefault(
                tuple(person.value for person in value), []
            ).append(title)

        # Remove empty values
        people_to_action.pop((), None)

        return ', '.join(
            f"{join_grammatically(titles)} by {join_grammatically(value)}"
            for value, titles in people_to_action.items()
        )


def main() -> None:
    tj: Trickjump = Trickjump({
            "name": "Test Jump"
        },
            required=False
    )

if __name__ == '__main__':
    main()