from collections import deque
from dataclasses import dataclass
import enum
from string.templatelib import Template
from types import EllipsisType, MappingProxyType
import typing as t

from discord_.errors import FeedbackError
from discord_.utils_.messaging import MessageStatus
from structures.attribute import AnyAttributeT
from structures.attribute.collection import Collection, CollectionEntry
from structures.attribute.slot_str import SlotStr, SlotTypeT
from structures.task.attribute_value_mapping import AttributeValueMapping
from utils.text import NormStr

class FilterSyntaxFeedbackError(FeedbackError):
    def __init__(
        self, 
        header: str, 
        core: Template, *, 
        additional: Template | None = None, 
        related_documentation: t.Sequence[tuple[str, str]] = (), 
        paragraphs: t.Sequence[Template] = (), 
        msg_kwargs: t.Mapping[str, t.Any] | None = None, 
        explicit_message_status: MessageStatus | None = None
    ):
        super().__init__(f"Filter Syntax Error: {header}", core, additional=additional, related_documentation=related_documentation, paragraphs=paragraphs, msg_kwargs=msg_kwargs, explicit_message_status=explicit_message_status)

class ExpectedButFoundFeedbackError(FilterSyntaxFeedbackError):
    def __init__(self, expected_header: str, expected_full: Template, but_found: Token) -> None:
        super().__init__(
            f"{expected_header} Expected",
            t"Expected " + expected_full + t", but found " + TOKEN_TO_ERR_DESCRIPTION[but_found.type](but_found) + t" instead!"
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
    yield Token(TokenType.START, '')

    string: list[str] = []

    def end_string():
        if not string:
            return
        
        s = ''.join(string)
        string.clear()

        # Case sensitive by design
        if s == '_':
            yield Token(TokenType.UNDERSCORE, s)
        
        elif s == 'or':
            yield Token(TokenType.OR, s)
        
        elif s == 'and':
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

        if c == '(':
            yield from end_string()
            yield Token(TokenType.LPAREN, c)
            continue

        if c == ')':
            yield from end_string()
            yield Token(TokenType.RPAREN, c)
            continue
        
        # Quoted String
        if c in '"\'':
            yield from end_string()

            quote: str = c
            escape: bool = False

            for c in it:
                if escape:
                    if c not in ('\\', quote):
                        raise FilterSyntaxFeedbackError(
                            "Invalid Escape Sequence",
                            t"The escape sequence {'\\' + c:,} is invalid!",
                            additional=t"The only characters allowed to be escaped (= put after a `\\`) are {('\\', quote):&}."
                        )
                    
                    escape = False
                    string.append(c)

                elif c == '\\':
                    escape = True

                elif c == quote:
                    break

                else:
                    string.append(c)
            else:
                raise FilterSyntaxFeedbackError(
                    "Unclosed Quotation Mark",
                    t"The quoted string {''.join(string) if string else ' ':,} was never closed!"
                )
            
            yield Token(TokenType.STR, ''.join(string))
            string.clear()

            continue
        
        # Unquoted String
        string.append(c)

    yield from end_string()
    yield Token(TokenType.END, '')


class Node: 
    pass

class BoolOp(Node): pass
class And(BoolOp): pass
class Or(BoolOp): pass

class Attr(Node):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

class Op(Node): pass
class Is(Op): pass
class IsNot(Op): pass
class Lt(Op): pass
class LtE(Op): pass
class Gt(Op): pass
class GtE(Op): pass

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
    def __init__(self, first: Comparison | BoolExpr, op: BoolOp, second: Comparison | BoolExpr, *others: Comparison | BoolExpr) -> None:
        super().__init__()
        self.first = first
        self.second = second
        self.op = op
        self.others = list(others)

OP_STR_TO_NODE_TYPE: t.Final[MappingProxyType[str, type[Op]]] = MappingProxyType({
    'is': Is,
    'not': IsNot,
    '<': Lt,
    '<=': LtE,
    '>': Gt,
    '>=': GtE
})

OPS: t.Final[tuple[str, ...]] = ('is', 'is not', '<', '<=', '>', '>=')

TOKEN_TO_ERR_DESCRIPTION: t.Final[MappingProxyType[TokenType, t.Callable[[Token], Template]]] = MappingProxyType({
    TokenType.START: lambda token: t"the start",
    TokenType.END: lambda token: t"the end",
    TokenType.AND: (and_or := lambda token: t"the keyword {token.string:,}"),
    TokenType.OR: and_or,
    TokenType.STR: lambda token: t"the string {token.string!r:,}",
    TokenType.OP: lambda token: t"the operator {token.string:,}",
    TokenType.LPAREN: lambda token: t"an opening parenthesis ({token.string:,})",
    TokenType.RPAREN: lambda token: t"a closing parenthesis ({token.string:,})",
    TokenType.UNDERSCORE: lambda token: t"the symbol for an empty value {token.string!r:,}"
})

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
            self._peeked = next(self._it, Token(TokenType.INVALID, ''))

        return self._peeked

def parse_op(ts: TokenStream) -> Op:
    op = next(ts)

    if op.type is not TokenType.OP:
        raise ExpectedButFoundFeedbackError(
            "Operator",
            t"an operator ({OPS:,})",
            op
        )
    
    op_type = OP_STR_TO_NODE_TYPE[op.string]

    if op_type is Is and (nxt := ts.peek()) and nxt.type is TokenType.OP and OP_STR_TO_NODE_TYPE[nxt.string] is IsNot:
        next(ts)
        op_type = IsNot

    return op_type()

def parse_comparison(ts: TokenStream) -> Comparison:
    attr = next(ts)

    if attr.type is not TokenType.STR:
        raise ExpectedButFoundFeedbackError(
            "Attribute",
            t"the name or alias of an attribute",
            attr
        )
    
    op = parse_op(ts)
    v = next(ts)

    if v.type is TokenType.STR:
        val = Val(v.string)
    elif v.type is TokenType.UNDERSCORE:
        val = Val(...)
    else:
        raise ExpectedButFoundFeedbackError(
            "Value",
            t"a value to be compared against",
            v
        )
    
    return Comparison(Attr(attr.string), op, val)

def parse_atom(ts: TokenStream) -> Comparison | BoolExpr:
    tok = ts.peek()

    if tok.type is TokenType.LPAREN:
        next(ts)

        expr = parse_or(ts)
        tok = next(ts)

        if tok.type is not TokenType.RPAREN:
            raise ExpectedButFoundFeedbackError(
                "Closing Parenthesis",
                t"a closing parenthesis ({')':,})",
                tok
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
        raise ExpectedButFoundFeedbackError(
            "Start",
            t"the start",
            first
        )

    expr = parse_or(ts)

    end = ts.peek()

    if end.type is not TokenType.END:
        raise ExpectedButFoundFeedbackError(
            "End",
            t"the end",
            end
        )

    return expr



class FilterCache:
    def __init__(self) -> None:
        self._norm_str_from_str_cache: dict[SlotStr, NormStr] = {}
        self._slot_type_cache: dict[tuple[AnyAttributeT, NormStr], SlotTypeT] = {}
        self._collection_cache: dict[AnyAttributeT, Collection] = {}
        self._collection_entry_cache: dict[
            tuple[AnyAttributeT, SlotTypeT], CollectionEntry
        ] = {}

    def _get_cached_norm_str(self, slot: SlotStr) -> NormStr:
        try:
            return self._norm_str_from_str_cache[slot]
        except KeyError:
            v = NormStr(slot)
            self._norm_str_from_str_cache[slot] = NormStr(slot)
            return v

    def _get_cached_slot_type(
        self, attr: AnyAttributeT, slot_str: SlotStr
    ) -> SlotTypeT:
        norm_str = self._get_cached_norm_str(slot_str)
        key = (attr, norm_str)

        try:
            return self._slot_type_cache[key]
        except KeyError:
            v = attr.slot_type(norm_str)
            self._slot_type_cache[key] = v
            return v

    def _get_cached_collection(self, attr: AnyAttributeT) -> Collection:
        try:
            return self._collection_cache[attr]
        except KeyError:
            v = attr.get_collection()
            self._collection_cache[attr] = v
            return v

    def _get_cached_collection_entry(
        self, attr: AnyAttributeT, slot_str: SlotTypeT
    ) -> CollectionEntry:
        key = (attr, slot_str)

        try:
            return self._collection_entry_cache[key]
        except KeyError:
            v = self._get_cached_collection(attr).get_entry_by_syn(
                NormStr(str(slot_str))
            )
            self._collection_entry_cache[key] = v
            return v

type FastAvmT = dict[int, dict[NormStr, frozenset[SlotTypeT]]]


def _handle_comparison(node: Comparison, fast_avms: FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: FilterCache) -> FastAvmT:
    ...

def _handle_node(
    node: Comparison | BoolExpr, 
    fast_avms: FastAvmT,
    syn_to_attr: dict[NormStr, AnyAttributeT],
    seen_attrs: set[AnyAttributeT],
    cache: FilterCache
) -> FastAvmT:
    if isinstance(node, Comparison):
        return _handle_comparison(node, fast_avms, syn_to_attr, seen_attrs, cache)
    

def run[T: AttributeValueMapping](
    s: str, 
    avms: t.Iterable[T],
    syn_to_attr: dict[NormStr, AnyAttributeT],
) -> tuple[list[AttributeValueMapping], set[AnyAttributeT]]:
    node = transform(tokenize(s))

    id_to_avm: dict[int, AttributeValueMapping] = {id(avm): avm for avm in avms}
    cache: FilterCache = FilterCache()

    fast_avms: FastAvmT = {
        id(avm): {
            attr.norm_name: frozenset(
                cache._get_cached_slot_type(attr, slot) for slot in val
            )
            for attr, val in avm.combined.items()
        }
        for avm in id_to_avm.values()
    }

    seen_attrs: set[AnyAttributeT] = set()

    return (
        [
            id_to_avm[id(avm)] 
            for avm in 
            _handle_node(node, fast_avms, syn_to_attr, seen_attrs, cache)
        ], 
        seen_attrs
    )


    