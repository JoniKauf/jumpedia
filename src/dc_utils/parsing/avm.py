import typing as t

from dc_utils import errors
from structures.attribute import AnyAttributeT, BaseAttribute
from utils import orm
from utils.text import NormStr, RealStr

from . import mapping


def parse[T: AnyAttributeT](
    session: Session, s: RealStr, syn_to_attr: t.Mapping[NormStr, T]
) -> dict[T, tuple[RealStr, ...]]:

    raw_avm = mapping.parse(s)

    res: dict[T, tuple[RealStr, ...]] = {}

    for attr_raw, value_raw in raw_avm:
        attr = syn_to_attr.get(NormStr(attr_raw))

        if attr is None:
            raise errors.StructureNotFoundViaSyn(attr_raw, BaseAttribute)

        if attr in res:
            raise errors.NotUniqueStructureInMapping(attr)

        res[attr] = tuple(map(RealStr, value_raw))

    return res
