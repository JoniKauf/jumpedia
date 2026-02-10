from utils.text import RealStr

from . import factory


class SyntaxError(factory.SyntaxFeedbackError, category="mapping"):
    pass


expected_but_received = factory.expected_but_received_factory(error_type=SyntaxError)


class TokenTypes(factory.TokenTypesWithParens):
    COLON = factory.TokenType(5, lambda token: t"a colon ({':':,})")


def _token_from_c(c: str) -> factory.Token | None:
    if c == "(":
        return factory.Token(TokenTypes.LPAREN, c)

    if c == ")":
        return factory.Token(TokenTypes.RPAREN, c)

    if c == ":":
        return factory.Token(TokenTypes.COLON, c)

    return None


def _token_from_buf(buf: str) -> factory.Token | None:
    return None


tokenize = factory.tokenize_factory(
    token_from_c=_token_from_c, token_from_buf=_token_from_buf, error_type=SyntaxError
)


class Key(factory.Node):
    def __init__(self, key: str) -> None:
        super().__init__()
        self.key = key


class Value(factory.Node):
    def __init__(self, value: str) -> None:
        super().__init__()
        self.value = value


class ValueCollection(factory.Node):
    def __init__(self, *values: Value) -> None:
        super().__init__()
        self.values = values


class Mapping(factory.Node):
    def __init__(self, key: Key, value_collection: ValueCollection) -> None:
        super().__init__()
        self.key = key
        self.value_collection = value_collection


class MappingCollection(factory.Node):
    def __init__(self, first: Mapping, *others: Mapping) -> None:
        super().__init__()
        self.first = first
        self.others = others


def _transform_value_collection(
    ts: factory.TokenStream, lparen: bool
) -> ValueCollection:
    values: list[Value] = []

    if lparen:
        while (tok := next(ts)).type is TokenTypes.STR:
            values.append(Value(tok.string))

        if tok.type is not TokenTypes.RPAREN:
            raise expected_but_received(t"a closing parenthesis {')':,}", tok)
    else:
        while (tok := ts.peek()).type is TokenTypes.STR:
            next(ts)

            if ts.peek().type is TokenTypes.COLON:
                ts.push(tok)
                break

            values.append(Value(tok.string))

    return ValueCollection(*values)


def _transform_mapping(ts: factory.TokenStream) -> Mapping:
    first = next(ts)

    lparen: bool
    key: factory.Token

    if first.type is TokenTypes.LPAREN:
        lparen = True
        key = next(ts)

        if key.type is not TokenTypes.STR:
            raise expected_but_received(t"a string representing the key", key)

    elif first.type is TokenTypes.STR:
        lparen = False
        key = first

    else:
        raise expected_but_received(
            t"either an opening parenthesis {'(':,} or a string representing the key",
            first,
        )

    colon = next(ts)

    if colon.type is not TokenTypes.COLON:
        raise expected_but_received(
            t"a colon ({':':,}) after the key {key.string:,}",
            colon,
        )

    return Mapping(Key(key.string), _transform_value_collection(ts, lparen))


def _transform_mapping_collection(ts: factory.TokenStream, _: int) -> MappingCollection:
    mapping_collection: list[Mapping] = []

    while (tok := ts.peek()).type is not TokenTypes.END:
        assert tok.type is not TokenTypes.INVALID

        mapping_collection.append(_transform_mapping(ts))

    if not mapping_collection:
        raise expected_but_received(t"mapping syntax", ts.peek())

    return MappingCollection(*mapping_collection)


transform = factory.transform_factory(
    transform=_transform_mapping_collection, expected_but_received=expected_but_received
)


def parse(s: RealStr) -> tuple[tuple[str, tuple[str, ...]], ...]:
    # RealStr cannot be empty

    mapping_collection = transform(tokenize(s))

    return tuple(
        (syns.key.key, tuple(value.value for value in syns.value_collection.values))
        for syns in (mapping_collection.first, *mapping_collection.others)
    )
