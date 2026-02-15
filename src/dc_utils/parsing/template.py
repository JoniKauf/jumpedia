# template.py

import typing as t
from string.templatelib import Template

from . import factory
from . import filter as filter_syntax


class SyntaxError(factory.SyntaxFeedbackError, category="template"):
    pass


expected_but_received = factory.expected_but_received_factory(error_type=SyntaxError)


class TokenTypes(factory.TokenTypesWithParens):
    IF = factory.TokenType(10, lambda _: t"the keyword {'if':,}")
    THEN = factory.TokenType(11, lambda _: t"the keyword {'then':,}")
    ELSE = factory.TokenType(12, lambda _: t"the keyword {'else':,}")
    PLUS = factory.TokenType(13, lambda _: t"the plus operator {'+':,}")
    INTERP = factory.TokenType(
        14, lambda token: t"an interpolation {{{token.string:,}}}"
    )


def _token_from_buf(buf: str) -> factory.Token | None:
    if buf == "if":
        return factory.Token(TokenTypes.IF, buf)
    if buf == "then":
        return factory.Token(TokenTypes.THEN, buf)
    if buf == "else":
        return factory.Token(TokenTypes.ELSE, buf)

    # delegate to filter tokenizer for filter keywords/operators (and, or, _, is, etc.)
    tkn = getattr(filter_syntax, "_token_from_buf")(
        buf
    )  # reuse filter tokenization rules
    if tkn is not None:
        return tkn

    return None


def _token_from_c(c: str) -> factory.Token | None:
    if c == "(":
        return factory.Token(TokenTypes.LPAREN, c)
    if c == ")":
        return factory.Token(TokenTypes.RPAREN, c)
    if c == "+":
        return factory.Token(TokenTypes.PLUS, c)

    # delegate to filter single-char tokens (if any)
    return getattr(filter_syntax, "_token_from_c")(c)


def _interp_handler(
    it: t.Iterator[str], error_type: type[SyntaxError]
) -> factory.Token:
    buf: list[str] = []
    depth = 1
    for c in it:
        if c == "{":
            depth += 1
            buf.append(c)
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
            buf.append(c)
        else:
            buf.append(c)
    else:
        raise error_type(
            t"The interpolation expression {''.join(buf) if buf else ' ':,} was never closed!"
        )

    inner = "".join(buf).strip()
    return factory.Token(TokenTypes.INTERP, inner)


def tokenize(s: str) -> t.Generator[factory.Token, None, None]:
    yield factory.Token(factory.TokenTypes.START, "")

    buf: list[str] = []
    it = iter(s)

    def _flush_buf() -> t.Generator[factory.Token, None, None]:
        if not buf:
            return
        joined = "".join(buf)
        buf.clear()
        tkn = _token_from_buf(joined)
        if tkn is not None:
            yield tkn
        else:
            yield factory.Token(factory.TokenTypes.STR, joined)

    for c in it:
        # quoted strings
        if c in "\"'":
            # consume quoted string (use factory's default handler)
            yield from _flush_buf()
            yield factory.default_quoted_handler(c, it, SyntaxError)
            continue

        # interpolation
        if c == "{":
            yield from _flush_buf()
            yield _interp_handler(it, SyntaxError)
            continue

        if c.isspace():
            yield from _flush_buf()
            continue

        # single-char tokens (parentheses, plus, etc.)
        if (tkn := _token_from_c(c)) is not None:
            yield from _flush_buf()
            yield tkn
            continue

        buf.append(c)

    yield from _flush_buf()
    yield factory.Token(factory.TokenTypes.END, "")


class Expr(factory.Node):
    pass


class Literal(Expr):
    def __init__(self, value: str) -> None:
        self.value = value


class Interpolation(Expr):
    def __init__(self, expr_str: str) -> None:
        self.expr_str = expr_str


class Concat(Expr):
    def __init__(self, parts: list[Expr]) -> None:
        self.parts = parts


class IfExpr(Expr):
    def __init__(
        self, condition: factory.Node, then_branch: Expr, else_branch: Expr
    ) -> None:
        self.condition = condition
        self.then_branch = then_branch
        self.else_branch = else_branch


check_depth = factory.check_depth_decorator_factory(127)


@check_depth
def _transform_atom(ts: factory.TokenStream, depth: int) -> Expr:
    depth += 1
    tok = ts.peek()

    if tok.type is TokenTypes.LPAREN:
        next(ts)
        expr = _transform_if(ts, depth)
        tok = next(ts)
        if tok.type is not TokenTypes.RPAREN:
            raise expected_but_received(t"a closing parenthesis ({')':,})", tok)
        return expr

    if tok.type is factory.TokenTypes.STR:
        next(ts)
        return Literal(tok.string)

    if tok.type is TokenTypes.INTERP:
        next(ts)
        # interpolation content is parsed by filter.tokenize/transform if it looks like filter,
        # but here we treat interpolation as a raw variable/expression string to be looked up at render time.
        # store the inner string
        return Interpolation(tok.string)

    if tok.type is TokenTypes.IF:
        return _transform_if(ts, depth)

    raise expected_but_received(t"a string or an expression", tok)


@check_depth
def _transform_concat(ts: factory.TokenStream, depth: int) -> Expr:
    depth += 1
    parts: list[Expr] = [_transform_atom(ts, depth)]

    while True:
        tok = ts.peek()

        if tok.type is TokenTypes.PLUS:
            next(ts)
            parts.append(_transform_atom(ts, depth))
            continue

        if tok.type in (
            factory.TokenTypes.STR,
            TokenTypes.LPAREN,
            TokenTypes.IF,
            TokenTypes.INTERP,
        ):
            parts.append(_transform_atom(ts, depth))
            continue

        break

    if len(parts) == 1:
        return parts[0]
    return Concat(parts)


@check_depth
def _transform_if(ts: factory.TokenStream, depth: int) -> Expr:
    depth += 1
    tok = ts.peek()

    if tok.type is not TokenTypes.IF:
        return _transform_concat(ts, depth)

    # consume IF
    next(ts)

    # collect raw token strings until THEN (preserve tokens as strings to re-tokenize with filter)
    cond_parts: list[str] = []
    while True:
        tok = ts.peek()
        if tok.type is TokenTypes.THEN:
            break
        if tok.type is factory.TokenTypes.END:
            raise expected_but_received(t"the keyword {'then':,}", tok)
        # consume and capture token.string
        cond_parts.append(next(ts).string)
    # consume THEN
    next(ts)

    cond_text = " ".join(cond_parts).strip()
    if not cond_text:
        raise SyntaxError(t"The condition in an { 'if':, } expression cannot be empty!")

    # produce a filter AST by tokenizing the condition text with the filter tokenizer
    condition_node = filter_syntax.transform(filter_syntax.tokenize(cond_text))

    then_branch = _transform_if(ts, depth)

    tok = ts.peek()
    if tok.type is TokenTypes.ELSE:
        next(ts)
        else_branch = _transform_if(ts, depth)
    else:
        else_branch = Literal("")

    return IfExpr(condition_node, then_branch, else_branch)


transform = factory.transform_factory(
    transform=_transform_if, expected_but_received=expected_but_received
)


def render(
    node: Expr,
    context: dict[str, t.Any],
    eval_filter: t.Callable[[factory.Node, dict[str, t.Any]], bool],
) -> str:
    if isinstance(node, Literal):
        return node.value

    if isinstance(node, Interpolation):
        key = node.expr_str.strip()
        # simple lookup; missing keys -> empty string
        val = context.get(key, "")
        return "" if val is None else str(val)

    if isinstance(node, Concat):
        return "".join(render(p, context, eval_filter) for p in node.parts)

    if isinstance(node, IfExpr):
        if eval_filter(node.condition, context):
            return render(node.then_branch, context, eval_filter)
        return render(node.else_branch, context, eval_filter)

    assert False
