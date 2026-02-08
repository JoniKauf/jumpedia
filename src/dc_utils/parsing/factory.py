import functools
import typing as t
from collections import deque
from string.templatelib import Template

from dc_utils.errors import FeedbackError


class SyntaxFeedbackError(FeedbackError):
    def __init_subclass__(cls, category: str) -> None:
        super().__init_subclass__()

        cls._category = category.title()

    def __init__(self, core: Template, *, additional: Template | None = None):
        super().__init__(
            f"{type(self)._category} Syntax Error", core, additional=additional
        )


class NestingError(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            "Too Much Nesting",
            t"The specified syntax is nested way too much, more than anybody would reasonably need!",
        )


def expected_but_received_factory[T: SyntaxFeedbackError](
    *, error_type: type[T]
) -> t.Callable[[Template, Token], T]:
    def expected_but_received(expected: Template, received: Token) -> T:
        assert received.type is not TokenTypes.INVALID

        return error_type(
            t"Expected "
            + expected
            + t", but received "
            + received.type.received(received)
            + t" instead!",
        )

    return expected_but_received


class TokenType(t.NamedTuple):
    id: int
    received: t.Callable[[Token], Template]


class TokenTypes:
    START = TokenType(0, lambda _: t"the start")
    END = TokenType(1, lambda _: t"the end")

    STR = TokenType(2, lambda token: t"the string {token.string!r:,}")

    INVALID = TokenType(255, lambda _: t"something unexpected")


class TokenTypesWithParens(TokenTypes):
    LPAREN = TokenType(
        3,
        lambda token: t"an opening parenthesis ({token.string:,})",
    )
    RPAREN = TokenType(
        4,
        lambda token: t"a closing parenthesis ({token.string:,})",
    )


class Token(t.NamedTuple):
    type: TokenType
    string: str


def tokenize_factory(
    *,
    token_from_c: t.Callable[[str], Token | None],
    token_from_buf: t.Callable[[str], Token | None],
    error_type: type[SyntaxFeedbackError],
) -> t.Callable[[str], t.Generator[Token]]:
    def tokenize(s: str):
        def _yield_from_buf() -> t.Generator[Token, None, None]:
            if not buf:
                return

            buf_joined = "".join(buf)
            buf.clear()

            yield (token_from_buf(buf_joined) or Token(TokenTypes.STR, buf_joined))

        yield Token(TokenTypes.START, "")

        buf: list[str] = []
        quote_buf: list[str] = []
        it: t.Iterator[str] = iter(s)

        for c in it:
            # Quoted String
            if c in "\"'":
                yield from _yield_from_buf()

                quote: str = c
                escape: bool = False

                for c in it:
                    if escape:
                        if c not in ("\\", quote):
                            raise error_type(
                                t"The escape sequence {'\\' + c:,} is invalid!",
                                additional=t"The only characters allowed to be escaped (= put after a `\\`) are {('\\', quote):&}.",
                            )

                        escape = False
                        quote_buf.append(c)

                    elif c == "\\":
                        escape = True

                    elif c == quote:
                        break

                    else:
                        quote_buf.append(c)
                else:
                    raise error_type(
                        t"The quoted string {''.join(quote_buf) if quote_buf else ' ':,} was never closed!",
                    )

                yield Token(TokenTypes.STR, "".join(quote_buf))
                quote_buf.clear()

                continue

            if c.isspace():
                yield from _yield_from_buf()
                continue

            if (token := token_from_c(c)) is not None:
                yield from _yield_from_buf()
                yield token
                continue

            # Unquoted String
            buf.append(c)

        yield from _yield_from_buf()
        yield Token(TokenTypes.END, "")

    return tokenize


INVALID_TOKEN = Token(TokenTypes.INVALID, "")


class TokenStream:
    def __init__(self, iterable: t.Iterable[Token]):
        self._it = iter(iterable)
        self._buf: deque[Token] = deque()

    def __iter__(self):
        return self

    def __next__(self):
        if self._buf:
            return self._buf.popleft()

        return next(self._it, INVALID_TOKEN)

    def peek(self) -> Token:
        if not self._buf:
            self._buf.append(next(self._it, INVALID_TOKEN))

        return self._buf[0]

    def push(self, token: Token) -> None:
        self._buf.appendleft(token)


class Node:
    pass


class String(Node):
    def __init__(self, s: str) -> None:
        super().__init__()
        self.s = s


EXPECTED_ATTR: Template = t"a string representing the name or alias of an attribute"


def transform_factory[T1: Node](
    *,
    transform: t.Callable[[TokenStream, int], T1],
    expected_but_received: t.Callable[[Template, Token], SyntaxFeedbackError],
) -> t.Callable[[t.Iterable[Token]], T1]:
    @functools.wraps(transform)
    def transform_(iterable: t.Iterable[Token]) -> T1:
        ts = TokenStream(iterable)

        first = next(ts)

        if first.type is not TokenTypes.START:
            raise expected_but_received(t"the start", first)

        try:
            expr = transform(ts, 0)
        except RecursionError:
            raise NestingError()

        end = ts.peek()

        if end.type is not TokenTypes.END:
            raise expected_but_received(t"the end", end)

        return expr

    return transform_


def check_depth_decorator_factory[T: Node](
    max: int,
) -> t.Callable[[t.Callable[[TokenStream, int], T]], t.Callable[[TokenStream, int], T]]:
    def check_depth(
        func: t.Callable[[TokenStream, int], T],
    ) -> t.Callable[[TokenStream, int], T]:
        @functools.wraps(func)
        def wrapper(ts: TokenStream, depth: int) -> T:
            if depth > max:
                raise RecursionError

            return func(ts, depth)

        return wrapper

    return check_depth
