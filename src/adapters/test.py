from collections import deque
from dataclasses import dataclass
import enum
import itertools
from pprint import pprint
from types import MappingProxyType
import typing as t

class TokenType(enum.Enum):
    START = enum.auto()
    AND = enum.auto()
    OR = enum.auto()
    LPAREN = enum.auto()
    RPAREN = enum.auto()

    STR = enum.auto()
    OP = enum.auto()
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
                        raise ValueError(f"Backslash not escaping \\ or {quote}")
                    
                    escape = False
                    string.append(c)

                elif c == '\\':
                    escape = True

                elif c == quote:
                    break

                else:
                    string.append(c)
            else:
                raise ValueError(f"Unclosed {quote}")
            
            yield Token(TokenType.STR, ''.join(string))
            string.clear()

            continue
        
        # Unquoted String
        string.append(c)

    yield from end_string()


class Expr: 
    pass

class Underscore(Expr): pass

class BoolOp(Expr): pass
class And(BoolOp): pass
class Or(BoolOp): pass

class Attr(Expr):
    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name

class Op(Expr): pass
class Is(Op): pass
class IsNot(Op): pass
class Lt(Op): pass
class LtE(Op): pass
class Gt(Op): pass
class GtE(Op): pass

class Val(Expr):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value

class Triple(Expr):
    def __init__(self, attr: Attr, op: Op, val: Val | Underscore) -> None:
        super().__init__()
        self.attr = attr
        self.op = op
        self.val = val


class BoolExpr(Expr):
    def __init__(self, first: Triple | BoolExpr, op: BoolOp, *others: Triple | BoolExpr) -> None:
        super().__init__()
        self.first = first
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
    
    def peek(self) -> Token | None:
        if self._peeked is None:
            self._peeked = next(self._it, None)

        return self._peeked

def parse_op(ts: TokenStream) -> Op:
    tok = next(ts)

    if tok.type is not TokenType.OP:
        raise ValueError
    
    op_type = OP_STR_TO_NODE_TYPE[tok.string]

    if op_type is Is and (nxt := ts.peek()) and nxt.type is TokenType.OP and OP_STR_TO_NODE_TYPE[nxt.string] is IsNot:
        next(ts)
        op_type = IsNot

    return op_type()

def parse_triple(ts: TokenStream) -> Triple:
    attr = next(ts)

    if attr.type is not TokenType.STR:
        raise ValueError
    
    op = parse_op(ts)
    v = next(ts)

    if v.type is TokenType.UNDERSCORE:
        val = Underscore()
    elif v.type is TokenType.STR:
        val = Val(v.string)
    else:
        raise ValueError("Val is not underscore or str")
    
    return Triple(Attr(attr.string), op, val)

def parse_atom(ts: TokenStream) -> Triple | BoolExpr:
    tok = ts.peek()

    if tok is None:
        raise ValueError("Stop after boolop")

    if tok.type is TokenType.LPAREN:
        next(ts)
        expr = parse_or(ts)

        if next(ts).type is not TokenType.RPAREN:
            raise ValueError("Unclosed )")
        
        return expr

    return parse_triple(ts)


def parse_and(ts: TokenStream) -> Triple | BoolExpr:
    first = parse_atom(ts)
    rest: list[Triple | BoolExpr] = []

    while (tok := ts.peek()) and tok.type is TokenType.AND:
        next(ts)
        rest.append(parse_atom(ts))

    if not rest:
        return first

    return BoolExpr(first, And(), *rest)


def parse_or(ts: TokenStream) -> Triple | BoolExpr:
    first = parse_and(ts)
    rest: list[Triple | BoolExpr] = []

    while (tok := ts.peek()) and tok.type is TokenType.OR:
        next(ts)
        rest.append(parse_and(ts))

    if not rest:
        return first

    return BoolExpr(first, Or(), *rest)


def transform(iterable: t.Iterable[Token]) -> Expr:
    ts = TokenStream(iterable)

    if next(ts).type is not TokenType.START:
        raise ValueError

    expr = parse_or(ts)

    if ts.peek() is not None:
        raise ValueError

    return expr

def dump(
    node, annotate_fields=True,
    *,
    indent=None, show_empty=False,
):
    """
    Return a formatted dump of the tree in node.  This is mainly useful for
    debugging purposes.  If annotate_fields is true (by default),
    the returned string will show the names and the values for fields.
    If annotate_fields is false, the result string will be more compact by
    omitting unambiguous field names.  Attributes such as line
    numbers and column offsets are not dumped by default.  If this is wanted,
    include_attributes can be set to true.  If indent is a non-negative
    integer or string, then the tree will be pretty-printed with that indent
    level. None (the default) selects the single line representation.
    If show_empty is False, then empty lists and fields that are None
    will be omitted from the output for better readability.
    """
    def _format(node, level=0):
        if indent is not None:
            level += 1
            prefix = '\n' + indent * level
            sep = ',\n' + indent * level
        else:
            prefix = ''
            sep = ', '
        if isinstance(node, Expr):
            cls = type(node)
            args = []
            args_buffer = []
            allsimple = True
            keywords = annotate_fields
            for name in node.__dict__:
                try:
                    value = getattr(node, name)
                except AttributeError:
                    keywords = True
                    continue
                if value is None and getattr(cls, name, ...) is None:
                    keywords = True
                    continue
                if not show_empty:
                    if value == []:
                        field_type = cls.__annotations__.get(name, object)
                        if getattr(field_type, '__origin__', ...) is list:
                            if not keywords:
                                args_buffer.append(repr(value))
                            continue
                    if not keywords:
                        args.extend(args_buffer)
                        args_buffer = []
                value, simple = _format(value, level)
                allsimple = allsimple and simple
                if keywords:
                    args.append('%s=%s' % (name, value))
                else:
                    args.append(value)
            if allsimple and len(args) <= 3:
                return '%s(%s)' % (node.__class__.__name__, ', '.join(args)), not args
            return '%s(%s%s)' % (node.__class__.__name__, prefix, sep.join(args)), False
        elif isinstance(node, list):
            if not node:
                return '[]', True
            return '[%s%s]' % (prefix, sep.join(_format(x, level)[0] for x in node)), False
        return repr(node), True

    if not isinstance(node, Expr):
        raise TypeError('expected AST, got %r' % node.__class__.__name__)
    if indent is not None and not isinstance(indent, str):
        indent = ' ' * indent
    return _format(node)[0]


while True:
    try:
        gen = tuple(tokenize(input("Input: ")))
    except ValueError as e:
        print(f"❌ Tokenization: {e}")
    else:
        try:
            trans = transform(gen)
        except ValueError as e:
            print(f"❌ Transformation: {e}")
        else:
            print("✅ Complete:", dump(trans, indent=4))
            
    print()
