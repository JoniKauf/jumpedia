import typing as t
from types import EllipsisType, MappingProxyType

from dc_utils import errors
from structures.attribute import AnyAttributeT, BaseAttribute
from structures.attribute.collection import Collection
from structures.attribute.slot_str import SlotStr, SlotTypeT
from structures.errors import CollectionEntryNotFoundError
from structures.task.attribute_value_mapping import AttributeValueMapping
from utils import orm
from utils.text import NormStr, RealStr

from . import factory

# --- Errors ---


class SyntaxError(factory.SyntaxFeedbackError, category="filter"):
    pass


expected_but_received = factory.expected_but_received_factory(error_type=SyntaxError)

# --- Tokenization ---

_OP_NAMES: t.Final[tuple[str, ...]] = ("is", "is not", "<", "<=", ">", ">=")


class TokenTypes(factory.TokenTypesWithParens):
    AND = factory.TokenType(5, lambda _: t"the keyword {'and':,}")
    OR = factory.TokenType(6, lambda _: t"the keyword {'or':,}")

    OP = factory.TokenType(7, lambda token: t"the operator {token.string:,}")
    UNDERSCORE = factory.TokenType(
        8, lambda token: t"the empty value symbol {token.string:,}"
    )


def _token_from_buf(buf: str) -> factory.Token | None:
    if buf == "or":
        return factory.Token(TokenTypes.OR, buf)

    elif buf == "and":
        return factory.Token(TokenTypes.AND, buf)

    elif buf == "_":
        return factory.Token(TokenTypes.UNDERSCORE, buf)

    elif buf in _OP_FIRST_SIGHT_STR_TO_NODE_TYPE:
        return factory.Token(TokenTypes.OP, buf)

    return None


def _token_from_c(c: str) -> factory.Token | None:
    if c == "(":
        return factory.Token(TokenTypes.LPAREN, c)

    if c == ")":
        return factory.Token(TokenTypes.RPAREN, c)

    return None


tokenize = factory.tokenize_factory(
    token_from_c=_token_from_c, token_from_buf=_token_from_buf, error_type=SyntaxError
)

# --- Transformation ---


class BoolOp(factory.Node):
    pass


class And(BoolOp):
    pass


class Or(BoolOp):
    pass


class Op(factory.Node):
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


class Empty(factory.Node):
    pass


class Comparison(factory.Node):
    def __init__(
        self, attr: factory.String, op: Op, val: factory.String | Empty
    ) -> None:
        super().__init__()
        self.attr = attr
        self.op = op
        self.val = val


class BoolExpr(factory.Node):
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


_OP_FIRST_SIGHT_STR_TO_NODE_TYPE: t.Final[MappingProxyType[str, type[Op]]] = (
    MappingProxyType({"is": Is, "not": IsNot, "<": Lt, "<=": LtE, ">": Gt, ">=": GtE})
)


check_depth_decorator = factory.check_depth_decorator_factory(127)


@check_depth_decorator
def _transform_op(ts: factory.TokenStream, _: int) -> Op:
    op = next(ts)

    if (
        op.type is not TokenTypes.OP
        or (op_type := _OP_FIRST_SIGHT_STR_TO_NODE_TYPE[op.string]) is IsNot
    ):
        raise expected_but_received(t"an operator ({_OP_NAMES:,})", op)

    if (
        op_type is Is
        and (nxt := ts.peek())
        and nxt.type is TokenTypes.OP
        and _OP_FIRST_SIGHT_STR_TO_NODE_TYPE[nxt.string] is IsNot
    ):
        next(ts)
        op_type = IsNot

    return op_type()


@check_depth_decorator
def _transform_comparison(ts: factory.TokenStream, depth: int) -> Comparison:
    depth += 1

    attr = next(ts)

    if attr.type is not TokenTypes.STR:
        raise expected_but_received(factory.EXPECTED_ATTR, attr)

    op = _transform_op(ts, depth)
    v = next(ts)

    if v.type is TokenTypes.STR:
        val = factory.String(v.string)
    elif v.type is TokenTypes.UNDERSCORE:
        val = Empty()
    else:
        raise expected_but_received(
            t"a string representing a value or the empty value symbol {'_':,} to compare the attribute against",
            v,
        )

    return Comparison(factory.String(attr.string), op, val)


@check_depth_decorator
def _transform_atom(ts: factory.TokenStream, depth: int) -> Comparison | BoolExpr:
    depth += 1

    tok = ts.peek()

    if tok.type is TokenTypes.LPAREN:
        next(ts)

        expr = _transform_or(ts, depth)
        tok = next(ts)

        if tok.type is not TokenTypes.RPAREN:
            raise expected_but_received(t"a closing parenthesis ({')':,})", tok)

        return expr

    return _transform_comparison(ts, depth)


@check_depth_decorator
def _transform_and(ts: factory.TokenStream, depth: int) -> Comparison | BoolExpr:
    depth += 1

    first = _transform_atom(ts, depth)
    rest: list[Comparison | BoolExpr] = []

    while ts.peek().type is TokenTypes.AND:
        next(ts)
        rest.append(_transform_atom(ts, depth))

    if not rest:
        return first

    return BoolExpr(first, And(), *rest)


@check_depth_decorator
def _transform_or(ts: factory.TokenStream, depth: int) -> Comparison | BoolExpr:
    depth += 1

    first = _transform_and(ts, depth)
    rest: list[Comparison | BoolExpr] = []

    while ts.peek().type is TokenTypes.OR:
        next(ts)
        rest.append(_transform_and(ts, depth))

    if not rest:
        return first

    return BoolExpr(first, Or(), *rest)


transform = factory.transform_factory(
    transform=_transform_or, expected_but_received=expected_but_received
)

# --- Run ---


class _Cache:
    def __init__(self) -> None:
        self._norm_str_from_str_cache: dict[SlotStr, NormStr] = {}
        self._slot_type_cache: dict[tuple[type[SlotTypeT], NormStr], SlotTypeT] = {}
        self._collection_cache: dict[AnyAttributeT, Collection] = {}
        self._collection_entry_index_cache: dict[
            tuple[Collection, NormStr], int | None
        ] = {}

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

    def real_str_to_collection_index(
        self, collection: Collection, real_str: RealStr
    ) -> int:
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

        raise errors.CollectionEntryNotFound(
            CollectionEntryNotFoundError(real_str, collection)
        )


_OP_TO_FUNC: t.Final[
    dict[type[factory.Node], t.Callable[[frozenset[SlotTypeT], SlotTypeT], bool]]
] = {
    Is: lambda tav, v: v in tav,
    IsNot: lambda tav, v: v not in tav,
    Lt: lambda tav, v: any(s < v for s in tav),  # pyright: ignore[reportOperatorIssue]
    LtE: lambda tav, v: any(
        s <= v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    Gt: lambda tav, v: any(s > v for s in tav),  # pyright: ignore[reportOperatorIssue]
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
    cache: _Cache,
) -> _FastAvmT:
    attr = syn_to_attr.get(NormStr(node.attr.s))

    if attr is None:
        raise errors.StructureNotFoundViaSyn(node.attr.s, BaseAttribute)

    op_func = _OP_TO_FUNC[type(node.op)]

    op = node.op

    if isinstance(node.val, Empty):
        if not isinstance(op, Is | IsNot):
            raise SyntaxError(
                t"The empty value symbol {'_':,} can only be used with the {('is', 'is not'):&} operator!"
            )

        MUST_BE_EMPTY = isinstance(op, Is)

        return {
            i: tav
            for i, tav in fast_avms.items()
            if (not tav.get(attr.norm_name)) == MUST_BE_EMPTY
        }

    value_real: RealStr = RealStr(node.val.s)
    value_norm: NormStr = NormStr(value_real)

    # Throws appropriate error in __new__ if invalid
    value_typed = attr.slot_type(
        SlotStr(
            RealStr(value_norm, check=False),
            attr.slot_type,
            attr.list.community.jumpedia.limits,
        )
    )

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
                cache.real_str_to_collection_index(
                    collection, RealStr(str(slot), check=False)
                )
                for slot in tav.get(attr.norm_name, frozenset())
            ),
            idx,
        )
    }


def _handle_bool_expr(
    c: orm.Cursor,
    node: BoolExpr,
    fast_avms: _FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: _Cache,
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

            checked_successfully = _handle_node(
                c, v, fast_avms, syn_to_attr, seen_attrs, cache
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
    cache: _Cache,
) -> _FastAvmT:
    if isinstance(node, BoolExpr):
        return _handle_bool_expr(c, node, fast_avms, syn_to_attr, seen_attrs, cache)

    if isinstance(node, Comparison):
        return _handle_comparison(c, node, fast_avms, syn_to_attr, seen_attrs, cache)

    t.assert_never(node)


def parse[T: AttributeValueMapping](
    c: orm.Cursor,
    s: RealStr,
    avms: t.Iterable[T],
    syn_to_attr: dict[NormStr, AnyAttributeT],
) -> tuple[list[T], set[AnyAttributeT]]:
    # RealStr cannot be empty

    node = transform(tokenize(s))

    id_to_avm: dict[int, T] = {id(avm): avm for avm in avms}
    cache: _Cache = _Cache()

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
            for avm_id in _handle_node(
                c, node, fast_avms, syn_to_attr, seen_attrs, cache
            )
        ],
        seen_attrs,
    )
