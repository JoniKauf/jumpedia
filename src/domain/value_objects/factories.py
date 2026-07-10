from domain.entities.base import BaseEntity
from domain.errors import business
from domain.value_objects.string import Str


def make_length_limited_str_store_type(
    name: str, limit: int, entity_type: type[BaseEntity]
) -> type[Str]:
    class ConstrainedStr(Str):
        def _validation(self) -> None:
            if len(self) < limit:
                raise business.NameTooLong(self, limit, entity_type)

    ConstrainedStr.__name__ = name
    ConstrainedStr.__qualname__ = (
        name if "." not in name else name.rpartition(".")[0] + "." + name
    )

    return ConstrainedStr
