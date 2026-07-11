


from domain.value_objects.filter import FilterT
from interfaces import dsls


def filter(s: str | None) -> FilterT | None:
    return None if s is None else dsls.filter.engine.FilterEngine().eval(s)