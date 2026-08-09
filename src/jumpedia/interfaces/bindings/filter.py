from jumpedia.domain.value_objects.filter import FilterT
from jumpedia.domain.value_objects.string import RealStr
from jumpedia.interfaces import dsls


def filter(s: str | None) -> FilterT | None:
    return None if s is None else dsls.filter.engine.FilterEngine().eval(str(RealStr(s)))
