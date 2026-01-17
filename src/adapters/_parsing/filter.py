import enum
import typing as t
from collections import deque
from dataclasses import dataclass
from string.templatelib import Template
from types import EllipsisType, MappingProxyType

from adapters import errors
from adapters.errors import FeedbackError, StructureNotFoundViaSyn
from discord_.utils_.message import MessageStatus
from structures.attribute import AnyAttributeT, BaseAttribute
from structures.attribute.collection import Collection, CollectionEntry
from structures.attribute.slot_str import SlotStr, SlotTypeT
from structures.errors import CollectionEntryNotFoundError
from structures.task.attribute_value_mapping import AttributeValueMapping
from utils import orm
from utils.text import NormStr, RealStr


class FilterError(FeedbackError):
    def __init__(
        self,
        core: Template,
        *,
        additional: Template | None = None,
        related_documentation: t.Sequence[tuple[str, str]] = (),
        paragraphs: t.Sequence[Template] = (),
        msg_kwargs: t.Mapping[str, t.Any] | None = None,
        explicit_message_status: MessageStatus | None = None,
    ):
        super().__init__(
            f"Filter Syntax Error",
            core,
            additional=additional,
            related_documentation=related_documentation,
            paragraphs=paragraphs,
            msg_kwargs=msg_kwargs,
            explicit_message_status=explicit_message_status,
        )


def expected_but_found_error(expected_full: Template, but_found: Token) -> FilterError:
    return FilterError(
        t"Expected "
        + expected_full
        + t", but found "
        + TOKEN_TO_ERR_DESCRIPTION[but_found.type](but_found)
        + t" instead!",
    )


class TokenType(enum.Enum):
    INVALID = enum.auto()

    START = enum.auto()
    END = enum.auto()

    AND = enum.auto()
    OR = enum.auto()

    LPAREN = enum.auto()
    RPAREN = enum.auto()

    OP = enum.auto()
    STR = enum.auto()
    UNDERSCORE = enum.auto()


class Token(t.NamedTuple):
    type: TokenType
    string: str


def tokenize(s: str) -> t.Generator[Token]:
    yield Token(TokenType.START, "")

    string: list[str] = []

    def end_string():
        if not string:
            return

        s = "".join(string)
        string.clear()

        # Case sensitive by design
        if s == "_":
            yield Token(TokenType.UNDERSCORE, s)

        elif s == "or":
            yield Token(TokenType.OR, s)

        elif s == "and":
            yield Token(TokenType.AND, s)

        elif s in OP_STR_TO_NODE_TYPE:
            yield Token(TokenType.OP, s)

        else:
            yield Token(TokenType.STR, s)

    it = iter(s)

    for c in it:
        if c.isspace():
            yield from end_string()
            continue

        if c == "(":
            yield from end_string()
            yield Token(TokenType.LPAREN, c)
            continue

        if c == ")":
            yield from end_string()
            yield Token(TokenType.RPAREN, c)
            continue

        # Quoted String
        if c in "\"'":
            yield from end_string()

            quote: str = c
            escape: bool = False

            for c in it:
                if escape:
                    if c not in ("\\", quote):
                        raise FilterError(
                            t"The escape sequence {'\\' + c:,} is invalid!",
                            additional=t"The only characters allowed to be escaped (= put after a `\\`) are {('\\', quote):&}.",
                        )

                    escape = False
                    string.append(c)

                elif c == "\\":
                    escape = True

                elif c == quote:
                    break

                else:
                    string.append(c)
            else:
                raise FilterError(
                    t"The quoted string {''.join(string) if string else ' ':,} was never closed!",
                )

            yield Token(TokenType.STR, "".join(string))
            string.clear()

            continue

        # Unquoted String
        string.append(c)

    yield from end_string()
    yield Token(TokenType.END, "")


class Node:
    pass


class BoolOp(Node):
    pass


class And(BoolOp):
    pass


class Or(BoolOp):
    pass


class Attr(Node):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name


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


OP_STR_TO_NODE_TYPE: t.Final[MappingProxyType[str, type[Op]]] = MappingProxyType(
    {"is": Is, "not": IsNot, "<": Lt, "<=": LtE, ">": Gt, ">=": GtE}
)

OPS: t.Final[tuple[str, ...]] = ("is", "is not", "<", "<=", ">", ">=")

TOKEN_TO_ERR_DESCRIPTION: t.Final[
    MappingProxyType[TokenType, t.Callable[[Token], Template]]
] = MappingProxyType(
    {
        TokenType.START: lambda token: t"the start",
        TokenType.END: lambda token: t"the end",
        TokenType.AND: (and_or := lambda token: t"the keyword {token.string:,}"),
        TokenType.OR: and_or,
        TokenType.STR: lambda token: t"the string {token.string!r:,}",
        TokenType.OP: lambda token: t"the operator {token.string:,}",
        TokenType.LPAREN: lambda token: t"an opening parenthesis ({token.string:,})",
        TokenType.RPAREN: lambda token: t"a closing parenthesis ({token.string:,})",
        TokenType.UNDERSCORE: lambda token: t"the symbol for an empty value {token.string!r:,}",
    }
)


class TokenStream:
    def __init__(self, gen: t.Iterable[Token]):
        self._it = iter(gen)
        self._peeked: Token | None = None

    def __iter__(self):
        return self

    def __next__(self):
        if self._peeked is None:
            return next(self._it)

        tok = self._peeked
        self._peeked = None
        return tok

    def peek(self) -> Token:
        if self._peeked is None:
            self._peeked = next(self._it, Token(TokenType.INVALID, ""))

        return self._peeked


def parse_op(ts: TokenStream) -> Op:
    op = next(ts)

    ERROR = expected_but_found_error(t"an operator ({OPS:,})", op)

    if op.type is not TokenType.OP:
        raise ERROR
    
    op_type = OP_STR_TO_NODE_TYPE[op.string]

    if op_type is IsNot:
        raise ERROR
    
    if (
        op_type is Is
        and (nxt := ts.peek())
        and nxt.type is TokenType.OP
        and OP_STR_TO_NODE_TYPE[nxt.string] is IsNot
    ):
        next(ts)
        op_type = IsNot

    return op_type()


def parse_comparison(ts: TokenStream) -> Comparison:
    attr = next(ts)

    if attr.type is not TokenType.STR:
        raise expected_but_found_error(
            t"the name or alias of an attribute", attr
        )

    op = parse_op(ts)
    v = next(ts)

    if v.type is TokenType.STR:
        val = Val(v.string)
    elif v.type is TokenType.UNDERSCORE:
        val = Val(...)
    else:
        raise expected_but_found_error(
            t"a value to be compared against", v
        )

    return Comparison(Attr(attr.string), op, val)


def parse_atom(ts: TokenStream) -> Comparison | BoolExpr:
    tok = ts.peek()

    if tok.type is TokenType.LPAREN:
        next(ts)

        expr = parse_or(ts)
        tok = next(ts)

        if tok.type is not TokenType.RPAREN:
            raise expected_but_found_error(
                t"a closing parenthesis ({')':,})", tok
            )

        return expr

    return parse_comparison(ts)


def parse_and(ts: TokenStream) -> Comparison | BoolExpr:
    first = parse_atom(ts)
    rest: list[Comparison | BoolExpr] = []

    while ts.peek().type is TokenType.AND:
        next(ts)
        rest.append(parse_atom(ts))

    if not rest:
        return first

    return BoolExpr(first, And(), *rest)


def parse_or(ts: TokenStream) -> Comparison | BoolExpr:
    first = parse_and(ts)
    rest: list[Comparison | BoolExpr] = []

    while ts.peek().type is TokenType.OR:
        next(ts)
        rest.append(parse_and(ts))

    if not rest:
        return first

    return BoolExpr(first, Or(), *rest)


def transform(iterable: t.Iterable[Token]) -> Comparison | BoolExpr:
    ts = TokenStream(iterable)

    first = next(ts)

    if first.type is not TokenType.START:
        raise expected_but_found_error(t"the start", first)

    expr = parse_or(ts)

    end = ts.peek()

    if end.type is not TokenType.END:
        raise expected_but_found_error(t"the end", end)

    return expr


class _FilterCache:
    def __init__(self) -> None:
        self._norm_str_from_str_cache: dict[SlotStr, NormStr] = {}
        self._slot_type_cache: dict[tuple[AnyAttributeT, NormStr], SlotTypeT] = {}
        self._collection_cache: dict[AnyAttributeT, Collection] = {}
        self._collection_entry_cache: dict[
            tuple[AnyAttributeT, SlotTypeT], CollectionEntry | None
        ] = {}

    def get_cached_norm_str(self, slot: SlotStr) -> NormStr:
        try:
            return self._norm_str_from_str_cache[slot]
        except KeyError:
            v = NormStr(slot)
            self._norm_str_from_str_cache[slot] = v
            return v

    def get_cached_slot_type(
        self, attr: AnyAttributeT, slot_str: SlotStr
    ) -> SlotTypeT:
        norm_str = self.get_cached_norm_str(slot_str)
        key = (attr, norm_str)

        try:
            return self._slot_type_cache[key]
        except KeyError:
            v = attr.slot_type(norm_str)
            self._slot_type_cache[key] = v
            return v

    def get_cached_collection(self, c: orm.Cursor, attr: AnyAttributeT) -> Collection:
        try:
            return self._collection_cache[attr]
        except KeyError:
            v = attr.get_collection(c)
            self._collection_cache[attr] = v
            return v

    def get_cached_collection_entry(
        self, c: orm.Cursor, attr: AnyAttributeT, norm_str: NormStr
    ) -> CollectionEntry | None:
        key = (attr, norm_str)

        try:
            return self._collection_entry_cache[key]
        except KeyError:
            v = self.get_cached_collection(c, attr).get_entry_by_syn(
                norm_str, None
            )
            self._collection_entry_cache[key] = v
            return v


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

type FastAvmT = dict[int, dict[NormStr, frozenset[SlotTypeT]]]


def _handle_comparison(
    c: orm.Cursor,
    node: Comparison,
    fast_avms: FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: _FilterCache,
) -> FastAvmT: 
    attr = syn_to_attr.get(NormStr(node.attr.name))

    if attr is None:
        raise errors.StructureNotFoundViaSyn(node.attr.name, BaseAttribute)
    
    op_func = _OP_TO_FUNC[node.op.__class__]

    value = node.val.value
    op = node.op

    if value is ...:
        if not isinstance(op, Is | IsNot):
            raise FilterError(
                t"The empty value symbol {'_':,} can only be used with the {('is', 'is not'):&} operator!"
            ) 
        
        MUST_BE_EMPTY = isinstance(op, Is)

        return {
            i: tav
            for i, tav in fast_avms.items()
            if (not tav.get(attr.norm_name)) is MUST_BE_EMPTY
        }
    
    value = RealStr(value)
    collection = cache.get_cached_collection(c, attr)

    if collection:
        entry = cache.get_cached_collection_entry(c, attr, SlotStr(value, attr.slot_type, attr.list.community.jumpedia.limits))

        if entry is None:
            raise errors.CollectionEntryNotFound(
                CollectionEntryNotFoundError(value, collection)
            )

        return {
            i: tav
            for i, tav in fast_avms.items()
            if op_func(
                frozenset(
                    cache.get_cached_collection_entry(c, attr, )
                    collection.get_entry_by_syn(NormStr(str(slot))).collection_index
                    for slot in tav.get(attr.norm_name, frozenset())
                ),
                entry.collection_index,
            )
        }

    value = attr.slot_type(value_str_norm)

    return {
        i: tav
        for i, tav in fast_avm.items()
        if op_func(tav.get(attr_name, frozenset()), value)
    }



def _handle_boolexpr(
    c: orm.Cursor,
    node: BoolExpr,
    fast_avms: FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: _FilterCache,
) -> FastAvmT: 
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
    fast_avms: FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: _FilterCache,
) -> FastAvmT:
    if isinstance(node, BoolExpr):
        return _handle_boolexpr(c, node, fast_avms, syn_to_attr, seen_attrs, cache)
    
    if isinstance(node, Comparison):
        return _handle_comparison(c, node, fast_avms, syn_to_attr, seen_attrs, cache)

    t.assert_never(node)

def run[T: AttributeValueMapping](
    c: orm.Cursor,
    s: str,
    avms: t.Iterable[T],
    syn_to_attr: dict[NormStr, AnyAttributeT],
) -> tuple[list[AttributeValueMapping], set[AnyAttributeT]]:
    node = transform(tokenize(s))

    id_to_avm: dict[int, AttributeValueMapping] = {id(avm): avm for avm in avms}
    cache: _FilterCache = _FilterCache()

    fast_avms: FastAvmT = {
        id(avm): {
            attr.norm_name: frozenset(
                cache.get_cached_slot_type(attr, slot) for slot in val
            )
            for attr, val in avm.combined.items()
        }
        for avm in id_to_avm.values()
    }

    seen_attrs: set[AnyAttributeT] = set()

    return (
        [
            id_to_avm[id(avm)]
            for avm in _handle_node(c, node, fast_avms, syn_to_attr, seen_attrs, cache)
        ],
        seen_attrs,
    )
