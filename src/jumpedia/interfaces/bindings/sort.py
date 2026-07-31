from jumpedia.domain.value_objects.attribute import AttributeSynStr
from jumpedia.interfaces import dsls


def sorts(s: str | None) -> tuple[tuple[AttributeSynStr, bool], ...]:
    return (
        ()
        if s is None
        else tuple(
            (AttributeSynStr(sort), asc)
            for sort, asc in dsls.sort.engine.SortEngine().eval(s)
        )
    )
