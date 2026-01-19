import enum
import typing as t
from string.templatelib import Template
from types import EllipsisType, MappingProxyType

from .. import errors
from . import Attr, Node, TokenTypes, TokenStream, TokenType, Token, check_depth_decorator_factory, expected_but_received_factory, tokenize_factory, transform_factory, SyntaxFeedbackError
from adapters.errors import FeedbackError
from discord_.utils_.message import MessageStatus
from structures.attribute import AnyAttributeT, BaseAttribute
from structures.attribute.collection import Collection
from structures.attribute.slot_str import SlotStr, SlotTypeT
from structures.errors import CollectionEntryNotFoundError
from structures.task.attribute_value_mapping import AttributeValueMapping
from utils import orm
from utils.text import NormStr, RealStr

# --- Errors ---

class FilterSyntaxError(SyntaxFeedbackError, category="filter"):
    pass

expected_but_received = expected_but_received_factory(error_type=FilterSyntaxError)

# --- Tokenization ---

_OP_NAMES: t.Final[tuple[str, ...]] = ("is", "is not", "<", "<=", ">", ">=")

class FilterTokenTypes(TokenTypes):
    LPAREN = TokenType(3, lambda token: t"an opening parenthesis ({token.string:,})",)
    RPAREN = TokenType(4, lambda token: t"a closing parenthesis ({token.string:,})",)

    AND = TokenType(5, lambda _: t"the keyword {'and':,}")
    OR = TokenType(6, lambda _: t"the keyword {'or':,}")

    OP = TokenType(7, lambda token: t"the operator {token.string:,}")
    UNDERSCORE = TokenType(8, lambda token: t"the empty value symbol {token.string:,}")


def _token_from_buf(buf: str) -> Token | None:
    if buf == "_":
        return Token(FilterTokenTypes.UNDERSCORE, buf)

    elif buf == "or":
        return Token(FilterTokenTypes.OR, buf)

    elif buf == "and":
        return Token(FilterTokenTypes.AND, buf)

    elif buf in _OP_FIRST_SIGHT_STR_TO_NODE_TYPE:
        return Token(FilterTokenTypes.OP, buf)
    
    return None


def _token_from_c(c: str) -> Token | None:
    if c == "(":
        return Token(FilterTokenTypes.LPAREN, c)

    if c == ")":
        return Token(FilterTokenTypes.RPAREN, c)

    return None


filter_tokenize = tokenize_factory(token_from_c=_token_from_c, token_from_buf=_token_from_buf, error_type=FilterSyntaxError)

# --- Transformation ---

class BoolOp(Node):
    pass

class And(BoolOp):
    pass


class Or(BoolOp):
    pass


class Op(Node):
    pass


class Is(Op):
    pass


class IsNot(Op):
    pass


class Lt(Op):
    pass


class LtE(Op):
    pass


class Gt(Op):
    pass


class GtE(Op):
    pass


class Val(Node):
    def __init__(self, value: str | EllipsisType) -> None:
        super().__init__()
        self.value = value


class Comparison(Node):
    def __init__(self, attr: Attr, op: Op, val: Val) -> None:
        super().__init__()
        self.attr = attr
        self.op = op
        self.val = val


class BoolExpr(Node):
    def __init__(
        self,
        first: Comparison | BoolExpr,
        op: BoolOp,
        second: Comparison | BoolExpr,
        *others: Comparison | BoolExpr,
    ) -> None:
        super().__init__()
        self.first = first
        self.second = second
        self.op = op
        self.others = list(others)

_OP_FIRST_SIGHT_STR_TO_NODE_TYPE: t.Final[MappingProxyType[str, type[Op]]] = MappingProxyType(
    {"is": Is, "not": IsNot, "<": Lt, "<=": LtE, ">": Gt, ">=": GtE}
)


check_depth_decorator = check_depth_decorator_factory(127)

@check_depth_decorator
def _parse_op(ts: TokenStream, _: int) -> Op:
    op = next(ts)

    if op.type is not FilterTokenTypes.OP or (op_type := _OP_FIRST_SIGHT_STR_TO_NODE_TYPE[op.string]) is IsNot:
        raise expected_but_received(t"an operator ({_OP_NAMES:,})", op)
    
    if (
        op_type is Is
        and (nxt := ts.peek())
        and nxt.type is FilterTokenTypes.OP
        and _OP_FIRST_SIGHT_STR_TO_NODE_TYPE[nxt.string] is IsNot
    ):
        next(ts)
        op_type = IsNot

    return op_type()

@check_depth_decorator
def _parse_comparison(ts: TokenStream, depth: int) -> Comparison:
    attr = next(ts)

    if attr.type is not FilterTokenTypes.STR:
        raise expected_but_received(
            Attr.expected, attr
        )

    op = _parse_op(ts, depth + 1)
    v = next(ts)

    if v.type is FilterTokenTypes.STR:
        val = Val(v.string)
    elif v.type is FilterTokenTypes.UNDERSCORE:
        val = Val(...)
    else:
        raise expected_but_received(
            t"a string representing a value or the empty value symbol {'_':,} to compare the attribute against", v
        )

    return Comparison(Attr(attr.string), op, val)

@check_depth_decorator
def _parse_atom(ts: TokenStream, depth: int) -> Comparison | BoolExpr:
    tok = ts.peek()

    if tok.type is FilterTokenTypes.LPAREN:
        next(ts)

        expr = _parse_or(ts, depth + 1)
        tok = next(ts)

        if tok.type is not FilterTokenTypes.RPAREN:
            raise expected_but_received(
                t"a closing parenthesis ({')':,})", tok
            )

        return expr

    return _parse_comparison(ts, depth + 1)

@check_depth_decorator
def _parse_and(ts: TokenStream, depth: int) -> Comparison | BoolExpr:
    first = _parse_atom(ts, depth + 1)
    rest: list[Comparison | BoolExpr] = []

    while ts.peek().type is FilterTokenTypes.AND:
        next(ts)
        rest.append(_parse_atom(ts, depth + 1))

    if not rest:
        return first

    return BoolExpr(first, And(), *rest)

@check_depth_decorator
def _parse_or(ts: TokenStream, depth: int) -> Comparison | BoolExpr:
    first = _parse_and(ts, depth + 1)
    rest: list[Comparison | BoolExpr] = []

    while ts.peek().type is FilterTokenTypes.OR:
        next(ts)
        rest.append(_parse_and(ts, depth + 1))

    if not rest:
        return first

    return BoolExpr(first, Or(), *rest)


filter_transform = transform_factory(parse=_parse_or, expected_but_received=expected_but_received)

# --- Run ---

class _FilterCache:
    def __init__(self) -> None:
        self._norm_str_from_str_cache: dict[SlotStr, NormStr] = {}
        self._slot_type_cache: dict[tuple[type[SlotTypeT], NormStr], SlotTypeT] = {}
        self._collection_cache: dict[AnyAttributeT, Collection] = {}
        self._collection_entry_index_cache: dict[tuple[Collection, NormStr], int | None] = {}

    def slot_str_to_slot_norm_str(self, slot: SlotStr) -> NormStr:
        try:
            return self._norm_str_from_str_cache[slot]
        except KeyError:
            v = NormStr(slot)
            self._norm_str_from_str_cache[slot] = v
            return v

    def slot_str_to_slot_type(
        self, slot_type: type[SlotTypeT], slot_str: SlotStr
    ) -> SlotTypeT:
        norm_str = self.slot_str_to_slot_norm_str(slot_str)
        key = (slot_type, norm_str)

        try:
            return self._slot_type_cache[key]
        except KeyError:
            v = slot_type(norm_str)
            self._slot_type_cache[key] = v
            return v

    def attribute_to_collection(self, c: orm.Cursor, attr: AnyAttributeT) -> Collection:
        try:
            return self._collection_cache[attr]
        except KeyError:
            v = attr.get_collection(c)
            self._collection_cache[attr] = v
            return v
        
    def real_str_to_collection_index(self, collection: Collection, real_str: RealStr) -> int:
        norm_str = NormStr(real_str)
        key = (collection, norm_str)

        try:
            v = self._collection_entry_index_cache[key]
        except KeyError:
            entry = collection.get_entry_by_syn(norm_str, None)

            if entry is not None:
                self._collection_entry_index_cache[key] = entry.collection_index
                return entry.collection_index
        else:
            if v is not None:
                return v
        
        raise errors.CollectionEntryNotFound(CollectionEntryNotFoundError(real_str, collection))
        


_OP_TO_FUNC: t.Final[
    dict[type[Node], t.Callable[[frozenset[SlotTypeT], SlotTypeT], bool]]
] = {
    Is: lambda tav, v: v in tav,
    IsNot: lambda tav, v: v not in tav,
    Lt: lambda tav, v: any(
        s < v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    LtE: lambda tav, v: any(
        s <= v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    Gt: lambda tav, v: any(
        s > v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    GtE: lambda tav, v: any(
        s >= v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
}

type _FastAvmT = dict[int, dict[NormStr, frozenset[SlotTypeT]]]

def _handle_comparison(
    c: orm.Cursor,
    node: Comparison,
    fast_avms: _FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: _FilterCache,
) -> _FastAvmT: 
    attr = syn_to_attr.get(NormStr(node.attr.syn))

    if attr is None:
        raise errors.StructureNotFoundViaSyn(node.attr.syn, BaseAttribute)

    op_func = _OP_TO_FUNC[type(node.op)]

    value = node.val.value
    op = node.op

    if value is ...:
        if not isinstance(op, Is | IsNot):
            raise FilterSyntaxError(
                t"The empty value symbol {'_':,} can only be used with the {('is', 'is not'):&} operator!"
            ) 
        
        MUST_BE_EMPTY = isinstance(op, Is)

        return {
            i: tav
            for i, tav in fast_avms.items()
            if (not tav.get(attr.norm_name)) == MUST_BE_EMPTY
        }
    
    value_real: RealStr = RealStr(value)
    del value
    
    # Throws appropriate error in __new__ if invalid
    value_typed = attr.slot_type(SlotStr(value_real, attr.slot_type, attr.list.community.jumpedia.limits))

    seen_attrs.add(attr)
    collection = cache.attribute_to_collection(c, attr)

    if not collection:
        return {
            i: tav
            for i, tav in fast_avms.items()
            if op_func(tav.get(attr.norm_name, frozenset()), value_typed)
        }
    
    idx = cache.real_str_to_collection_index(collection, value_real)

    if idx is None:
        raise errors.CollectionEntryNotFound(
            CollectionEntryNotFoundError(value_real, collection)
        )

    return {
        i: tav
        for i, tav in fast_avms.items()
        if op_func(
            frozenset(
                cache.real_str_to_collection_index(collection, RealStr(str(slot), check=False))
                for slot in tav.get(attr.norm_name, frozenset())
            ),
            idx
        )
    }

def _handle_boolexpr(
    c: orm.Cursor,
    node: BoolExpr,
    fast_avms: _FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: _FilterCache,
) -> _FastAvmT: 
    fast_avms = fast_avms.copy()

    if isinstance(node.op, Or):
        remaining_to_check = fast_avms
        result: dict[int, dict[NormStr, frozenset[SlotTypeT]]] = {}

        for v in (node.first, node.second, *node.others):
            if not remaining_to_check:
                break

            checked_successfully = _handle_node(
                c, v, remaining_to_check, syn_to_attr, seen_attrs, cache
            )

            for k in checked_successfully:
                remaining_to_check.pop(k, None)

            result |= checked_successfully

        return result

    if isinstance(node.op, And):
        for v in (node.first, node.second, *node.others):
            if not fast_avms:
                break

            checked_successfully = _handle_node(c,
                v, fast_avms, syn_to_attr, seen_attrs, cache
            )
            fast_avms = {
                k: v for k, v in fast_avms.items() if k in checked_successfully
            }

        return fast_avms

    t.assert_never(node.op)  # type: ignore

def _handle_node(
    c: orm.Cursor,
    node: Comparison | BoolExpr,
    fast_avms: _FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: _FilterCache,
) -> _FastAvmT:
    if isinstance(node, BoolExpr):
        return _handle_boolexpr(c, node, fast_avms, syn_to_attr, seen_attrs, cache)
    
    if isinstance(node, Comparison):
        return _handle_comparison(c, node, fast_avms, syn_to_attr, seen_attrs, cache)

    t.assert_never(node)


def run[T: AttributeValueMapping](
    c: orm.Cursor,
    s: RealStr,
    avms: t.Iterable[T],
    syn_to_attr: dict[NormStr, AnyAttributeT],
) -> tuple[list[T], set[AnyAttributeT]]:
    if not s:
        return list(avms), set()
    
    node = filter_transform(filter_tokenize(s))

    id_to_avm: dict[int, T] = {id(avm): avm for avm in avms}
    cache: _FilterCache = _FilterCache()

    fast_avms: _FastAvmT = {
        id(avm): {
            attr.norm_name: frozenset(
                cache.slot_str_to_slot_type(attr.slot_type, slot) for slot in val
            )
            for attr, val in avm.combined.items()
        }
        for avm in id_to_avm.values()
    }

    seen_attrs: set[AnyAttributeT] = set()

    return (
        [
            id_to_avm[avm_id]
            for avm_id in _handle_node(c, node, fast_avms, syn_to_attr, seen_attrs, cache)
        ],
        seen_attrs,
    )