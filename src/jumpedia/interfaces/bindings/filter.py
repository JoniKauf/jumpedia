from jumpedia.domain.value_objects.filter import FilterT
from jumpedia.interfaces import dsls
from jumpedia.interfaces.bindings import common


def filter(s: str | None) -> FilterT | None:
    return None if s is None else dsls.filter.engine.FilterEngine().eval(common.build_dsl_input(s))
