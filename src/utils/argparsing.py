import enum
from typing import Callable, Hashable


class State(enum.Enum):
    pass


class ArgParseState(State):
    OUT_QUOTES_AFTER_COMMA = enum.auto()
    IN_QUOTES = enum.auto()
    IN_ESCAPE = enum.auto()
    OUT_QUOTES_BEFORE_COMMA = enum.auto()


class KwargParseState(State):
    KW_OUT_BEFORE_SPACE = enum.auto()
    KW_OUT_AFTER_SPACE = enum.auto()
    KW_IN_QUOTES = enum.auto()
    KW_IN_ESCAPE = enum.auto()
    BEFORE_EQUAL = enum.auto()
    AFTER_EQUAL = enum.auto()
    V_OUT_QUOTES_AFTER_COMMA = enum.auto()
    V_IN_QUOTES = enum.auto()
    V_IN_ESCAPE = enum.auto()
    V_OUT_QUOTES_BEFORE_COMMA = enum.auto()


class UnexpectedCharError(ValueError):
    def __init__(self, state: State, s: str, i: int) -> None:
        self.state = state
        self.s = s
        self.i = i

        super().__init__(state, s, i)


def parse_args(s: str, /) -> list[str]:
    state: ArgParseState = ArgParseState.OUT_QUOTES_AFTER_COMMA
    arg: list[str] = []
    args: list[str] = []

    for i, c in enumerate(s):
        match state:
            case ArgParseState.OUT_QUOTES_AFTER_COMMA:
                if c == '"':
                    state = ArgParseState.IN_QUOTES
                elif not c.isspace():
                    raise UnexpectedCharError(state, s, i)

            case ArgParseState.IN_QUOTES:
                if c == '"':
                    args.append("".join(arg))
                    arg = []
                    state = ArgParseState.OUT_QUOTES_BEFORE_COMMA
                elif c == "\\":
                    state = ArgParseState.IN_ESCAPE
                else:
                    arg.append(c)

            case ArgParseState.IN_ESCAPE:
                if c not in '"\\':
                    raise UnexpectedCharError(state, s, i)

                arg.append(c)
                state = ArgParseState.IN_QUOTES

            case ArgParseState.OUT_QUOTES_BEFORE_COMMA:
                if c == ",":
                    state = ArgParseState.OUT_QUOTES_AFTER_COMMA
                elif not c.isspace():
                    raise UnexpectedCharError(state, s, i)

    if state not in (
        ArgParseState.OUT_QUOTES_BEFORE_COMMA,
        ArgParseState.OUT_QUOTES_AFTER_COMMA,
    ):
        raise UnexpectedCharError(state, "", len(s))

    return args


def parse_kwargs[TK: Hashable = str](
    s: str, /, transform_key: Callable[[str], TK] = lambda k: k
) -> dict[TK, list[str]]:
    state: KwargParseState = KwargParseState.KW_OUT_AFTER_SPACE
    kw: list[str] = []
    arg: list[str] = []
    args: list[str] = []
    kwargs: dict[TK, list[str]] = {}

    def item_complete():
        nonlocal state, kw, args, arg
        assert not arg

        k = transform_key("".join(kw))

        if k in kwargs:
            raise KeyError("key taken")

        kwargs[k] = args
        kw = []
        args = []

    for i, c in enumerate(s):
        match state:
            case KwargParseState.KW_OUT_AFTER_SPACE:
                if c == '"':
                    state = KwargParseState.KW_IN_QUOTES
                elif not c.isspace():
                    raise UnexpectedCharError(state, s, i)

            case KwargParseState.KW_IN_QUOTES:
                if c == '"':
                    state = KwargParseState.BEFORE_EQUAL
                elif c == "\\":
                    state = KwargParseState.KW_IN_ESCAPE
                else:
                    kw.append(c)

            case KwargParseState.KW_IN_ESCAPE:
                if c not in '"\\':
                    raise UnexpectedCharError(state, s, i)

                kw.append(c)
                state = KwargParseState.KW_IN_QUOTES

            case KwargParseState.BEFORE_EQUAL:
                if c == "=":
                    state = KwargParseState.AFTER_EQUAL
                elif not c.isspace():
                    raise UnexpectedCharError(state, s, i)

            case KwargParseState.AFTER_EQUAL:
                if c == "[":
                    state = KwargParseState.V_OUT_QUOTES_AFTER_COMMA
                elif not c.isspace():
                    raise UnexpectedCharError(state, s, i)

            case KwargParseState.V_OUT_QUOTES_AFTER_COMMA:
                if c == '"':
                    state = KwargParseState.V_IN_QUOTES
                elif c == "]":
                    item_complete()
                    state = KwargParseState.KW_OUT_BEFORE_SPACE
                elif not c.isspace():
                    raise UnexpectedCharError(state, s, i)

            case KwargParseState.V_IN_QUOTES:
                if c == '"':
                    args.append("".join(arg))
                    arg = []
                    state = KwargParseState.V_OUT_QUOTES_BEFORE_COMMA
                elif c == "\\":
                    state = KwargParseState.V_IN_ESCAPE
                else:
                    arg.append(c)

            case KwargParseState.V_IN_ESCAPE:
                if c not in '"\\':
                    raise UnexpectedCharError(state, s, i)

                arg.append(c)
                state = KwargParseState.V_IN_QUOTES

            case KwargParseState.V_OUT_QUOTES_BEFORE_COMMA:
                if c == ",":
                    state = KwargParseState.V_OUT_QUOTES_AFTER_COMMA
                elif c == "]":
                    item_complete()
                    state = KwargParseState.KW_OUT_BEFORE_SPACE
                elif not c.isspace():
                    raise UnexpectedCharError(state, s, i)

            case KwargParseState.KW_OUT_BEFORE_SPACE:
                if not c.isspace():
                    raise UnexpectedCharError(state, s, i)

                state = KwargParseState.KW_OUT_AFTER_SPACE

    if not state in (
        KwargParseState.KW_OUT_BEFORE_SPACE,
        KwargParseState.KW_OUT_AFTER_SPACE,
    ):
        raise UnexpectedCharError(state, "", len(s))

    return kwargs


def __main() -> None:
    import time

    while True:
        inp = input("Input: ")
        try:
            start = time.perf_counter()
            result = parse_kwargs(inp)
        except (KeyError, UnexpectedCharError) as e:
            result = e.__class__.__name__, e.__dict__
        finally:
            end = time.perf_counter()

        print(f"Result [{end - start:.4f}s]:", result, end="\n\n")


if __name__ == "__main__":
    __main()
