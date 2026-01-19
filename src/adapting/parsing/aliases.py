
from utils.text import RealStr
from . import factory

class SyntaxError(factory.SyntaxFeedbackError, category="aliases"):
    pass


expected_but_received = factory.expected_but_received_factory(error_type=SyntaxError)


class TokenTypes(factory.TokenTypes):
    pass


def _token_from_c(c: str) -> factory.Token | None:
    return None

def _token_from_buf(buf: str) -> factory.Token | None:
    return None


tokenize = factory.tokenize_factory(token_from_c=_token_from_c, token_from_buf=_token_from_buf, error_type=SyntaxError)


class Sequence(factory.Node):
    def __init__(self, first: factory.String, *others: factory.String) -> None:
        super().__init__()
        self.first = first
        self.others = others


def _transform_sequence(ts: factory.TokenStream, _: int) -> Sequence:
    lst: list[factory.String] = []

    while (tok := next(ts)) is TokenTypes.STR:
        lst.append(factory.String(tok.string))
    
    if tok.type is not TokenTypes.END:
        raise expected_but_received(t"either more aliases or the end", tok)

    if not lst:
        raise expected_but_received(t"at least one alias", tok)
    
    return Sequence(*lst)

transform = factory.transform_factory(transform=_transform_sequence, expected_but_received=expected_but_received)


def parse(
    s: RealStr,
) -> tuple[str, ...]:
    seq_node = transform(tokenize(s))

    return tuple(elem.s for elem in (seq_node.first, *seq_node.others))