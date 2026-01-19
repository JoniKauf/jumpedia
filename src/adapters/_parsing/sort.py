
import functools
import typing as t

from structures.attribute import AnyAttributeT, BaseAttribute
from structures.attribute.collection import Collection
from structures.task import Task
from structures.task.attribute_value_mapping import AttributeValueMapping
from utils import orm
from utils.text import NormStr, RealStr
from . import Attr, Node, Token, TokenStream, TokenTypes, TokenType, expected_but_received_factory, tokenize_factory, transform_factory, SyntaxFeedbackError
from adapters import errors

class SortSyntaxError(SyntaxFeedbackError, category="sort"):
    pass

class SortTokenTypes(TokenTypes):
    MINUS = TokenType(3, lambda tok: t"the descending order symbol {'-':,}")
    PLUS = TokenType(4, lambda tok: t"the ascending order symbol {'+':,}")

expected_but_received = expected_but_received_factory(error_type=SortSyntaxError)

def _token_from_c(c: str) -> Token | None:
    if c == '+':
        return Token(SortTokenTypes.PLUS, c)
    
    if c == '-':
        return Token(SortTokenTypes.MINUS, c)
    
    return None

def _token_from_buf(buf: str) -> Token | None:
    return None

_ORDER_OPS = ('+', '-')

sort_tokenize = tokenize_factory(token_from_c=_token_from_c, token_from_buf=_token_from_buf, error_type=SortSyntaxError)

class Order(Node):
    pass

class Asc(Order):
    pass

class Desc(Order):
    pass


class Sort(Node):
    def __init__(self, order: Order, attr: Attr) -> None:
        super().__init__()
        self.order = order
        self.attr = attr


class Sorts(Node):
    def __init__(self, first: Sort, *others: Sort) -> None:
        super().__init__()
        self.first = first
        self.others = others


def _parse_sort(ts: TokenStream) -> Sort:
    order = next(ts)

    if order.type not in (SortTokenTypes.PLUS, SortTokenTypes.MINUS):
        raise expected_but_received(t"the ascending or descending operator {('+', '-'):|}", order)
    
    attr = next(ts)

    if attr.type is not SortTokenTypes.STR:
        raise expected_but_received(Attr.expected, attr)
    
    return Sort(Asc() if order.type is SortTokenTypes.PLUS else Desc(), Attr(attr.string))
    

def _parse_sorts(ts: TokenStream, _: int) -> Sorts:
    sorts: list[Sort] = []

    while ts.peek().type not in (SortTokenTypes.END, SortTokenTypes.INVALID):
        sorts.append(_parse_sort(ts))

    if not sorts:
        raise expected_but_received(t"sort syntax", ts.peek())
    
    return Sorts(*sorts)


sort_transform = transform_factory(parse=_parse_sorts, expected_but_received=expected_but_received)



def sort[T: AttributeValueMapping](
    c: orm.Cursor, avms: t.Iterable[T], sorts: t.Iterable[tuple[AnyAttributeT, bool]]
) -> list[T]:
    # Remove duplicates while preserving order
    seen_attrs: set[AnyAttributeT] = set()
    sorts_unique: list[tuple[AnyAttributeT, bool]] = []

    for sort in sorts:
        attr, _ = sort

        if attr in seen_attrs:
            continue

        seen_attrs.add(attr)
        sorts_unique.append(sort)

    del seen_attrs, sorts

    attr_to_coll: dict[AnyAttributeT, Collection] = {
        attr: attr.get_collection(c) for attr, _ in sorts_unique
    }
    task_to_sort_value: dict[Task, list[tuple[t.Any, ...]]] = {}

    for avm in avms:
        result: list[tuple[t.Any, ...]] = []

        for attr, _ in sorts_unique:
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

        for va, vb, (_, asc) in zip(values_a, values_b, sorts_unique):
            if va < vb:
                return -1 if asc else 1

            if va > vb:
                return 1 if asc else -1

        return 0

    return sorted(avms, key=functools.cmp_to_key(cmp_key))  # type: ignore


def run[T: AttributeValueMapping](
    c: orm.Cursor,
    s: RealStr,
    avms: t.Iterable[T],
    syn_to_attr: dict[NormStr, AnyAttributeT],
) -> tuple[list[T], set[AnyAttributeT]]:
    if not s:
        return list(avms), set()
    
    sorts_node = sort_transform(sort_tokenize(s.strip()))
    sorts_extracted: list[tuple[AnyAttributeT, bool]] = []
    used_attributes: set[AnyAttributeT] = set()

    for sort_elem in (sorts_node.first, *sorts_node.others):
        attr = syn_to_attr.get(NormStr(sort_elem.attr.syn))

        if attr is None:
            raise errors.StructureNotFoundViaSyn(sort_elem.attr.syn, BaseAttribute)
        
        asc = isinstance(sort_elem.order, Asc)

        sorts_extracted.append((attr, asc))
        used_attributes.add(attr)

    return sort(c, avms, sorts_extracted), used_attributes