import functools
import typing as t

from dc_utils import errors
from structures.attribute import AnyAttributeT, BaseAttribute
from structures.attribute.collection import Collection
from structures.task import Task
from structures.task.attribute_value_mapping import AttributeValueMapping
from utils import orm
from utils.text import NormStr, RealStr

from . import factory


class SyntaxError(factory.SyntaxFeedbackError, category="sort"):
    pass


class TokenTypes(factory.TokenTypes):
    MINUS = factory.TokenType(5, lambda tok: t"the descending order symbol {'-':,}")
    PLUS = factory.TokenType(6, lambda tok: t"the ascending order symbol {'+':,}")


expected_but_received = factory.expected_but_received_factory(error_type=SyntaxError)


def _token_from_c(c: str) -> factory.Token | None:
    if c == "+":
        return factory.Token(TokenTypes.PLUS, c)

    if c == "-":
        return factory.Token(TokenTypes.MINUS, c)

    return None


def _token_from_buf(buf: str) -> factory.Token | None:
    return None


_ORDER_OPS = ("+", "-")

tokenize = factory.tokenize_factory(
    token_from_c=_token_from_c, token_from_buf=_token_from_buf, error_type=SyntaxError
)


class Order(factory.Node):
    pass


class Asc(Order):
    pass


class Desc(Order):
    pass


class Sort(factory.Node):
    def __init__(self, order: Order, attr: factory.String) -> None:
        super().__init__()
        self.order = order
        self.attr = attr


class SortCollection(factory.Node):
    def __init__(self, first: Sort, *others: Sort) -> None:
        super().__init__()
        self.first = first
        self.others = others


def _transform_sort(ts: factory.TokenStream) -> Sort:
    order = next(ts)

    if order.type not in (TokenTypes.PLUS, TokenTypes.MINUS):
        raise expected_but_received(
            t"the ascending or descending operator {_ORDER_OPS:|}", order
        )

    attr = next(ts)

    if attr.type is not TokenTypes.STR:
        raise expected_but_received(factory.EXPECTED_ATTR, attr)

    return Sort(
        Asc() if order.type is TokenTypes.PLUS else Desc(), factory.String(attr.string)
    )


def _transform_sort_collection(ts: factory.TokenStream, _: int) -> SortCollection:
    sorts: list[Sort] = []

    while ts.peek().type not in (TokenTypes.END, TokenTypes.INVALID):
        sorts.append(_transform_sort(ts))

    if not sorts:
        raise expected_but_received(t"sort syntax", ts.peek())

    return SortCollection(*sorts)


transform = factory.transform_factory(
    transform=_transform_sort_collection, expected_but_received=expected_but_received
)


def sort[T: AttributeValueMapping](
    c: orm.Cursor, avms: t.Iterable[T], sorts: t.Iterable[tuple[AnyAttributeT, bool]]
) -> list[T]:
    # Remove duplicates while preserving order
    seen_attrs: set[AnyAttributeT] = set()
    sorts_unique_and_simplified: list[tuple[AnyAttributeT, bool]] = []

    for sort in sorts:
        attr, _ = sort

        if attr in seen_attrs:
            continue

        seen_attrs.add(attr)
        sorts_unique_and_simplified.append(sort)

        # If the slots are unique, there is no point in any more lower priority sorts, it won't change
        if attr.unique_slots_across_list:
            break

    del seen_attrs, sorts

    attr_to_coll: dict[AnyAttributeT, Collection] = {
        attr: attr.get_collection(c) for attr, _ in sorts_unique_and_simplified
    }
    task_to_sort_value: dict[Task, list[tuple[t.Any, ...]]] = {}

    for avm in avms:
        result: list[tuple[t.Any, ...]] = []

        for attr, _ in sorts_unique_and_simplified:
            coll = attr_to_coll[attr]

            if coll:
                result.append(
                    tuple(
                        coll.get_entry_by_syn(NormStr(slot)).collection_index
                        for slot in avm.combined.get(attr, ())  # type: ignore
                    )
                )
            else:
                result.append(
                    tuple(
                        attr.slot_type(NormStr(slot))
                        for slot in avm.combined.get(attr, ())  # type: ignore
                    )
                )

        task_to_sort_value[avm.task] = result

    def cmp_key(a: T, b: T) -> int:
        values_a = task_to_sort_value[a.task]
        values_b = task_to_sort_value[b.task]

        for va, vb, (_, asc) in zip(values_a, values_b, sorts_unique_and_simplified):
            if va < vb:
                return -1 if asc else 1

            if va > vb:
                return 1 if asc else -1

        return 0

    return sorted(avms, key=functools.cmp_to_key(cmp_key))  # type: ignore


def parse[T: AttributeValueMapping](
    c: orm.Cursor,
    s: RealStr,
    avms: t.Iterable[T],
    syn_to_attr: dict[NormStr, AnyAttributeT],
) -> tuple[list[T], set[AnyAttributeT]]:
    # RealStr cannot be empty

    sorts_node = transform(tokenize(s.strip()))
    sorts_extracted: list[tuple[AnyAttributeT, bool]] = []
    used_attributes: set[AnyAttributeT] = set()

    for sort_elem in (sorts_node.first, *sorts_node.others):
        attr = syn_to_attr.get(NormStr(sort_elem.attr.s))

        if attr is None:
            raise errors.StructureNotFoundViaSyn(sort_elem.attr.s, BaseAttribute)

        asc = isinstance(sort_elem.order, Asc)

        sorts_extracted.append((attr, asc))
        used_attributes.add(attr)

    return sort(c, avms, sorts_extracted), used_attributes
