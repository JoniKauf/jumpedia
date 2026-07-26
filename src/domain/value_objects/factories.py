lazy from domain.entities.base import BaseEntity
from domain.enums.concept import Concept
from domain.errors.business import StrTooLong

lazy from domain.value_objects.string import Str


def make_length_limited_str_store_type(
    name: str, limit: int, concept: Concept
) -> type[Str]:
    class ConstrainedStr(Str):
        def _validation(self) -> None:
            if len(self) >= limit:
                raise StrTooLong(concept, self, limit)

    ConstrainedStr.__name__ = name
    ConstrainedStr.__qualname__ = (
        name if "." not in name else name.rpartition(".")[0] + "." + name
    )

    return ConstrainedStr
