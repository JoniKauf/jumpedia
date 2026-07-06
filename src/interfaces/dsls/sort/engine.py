from interfaces.dsls.sort import parse
from interfaces.dsls.shared import lex, parsing


def eval(s: str) -> list[tuple[str, bool]]:
    toks = lex.lex(s, multiline_strings=False)
    ast = parse.parse(toks)
    return [
        (parsing.get_string_from_text_node(elem.value), elem.asc)
        for elem in ast.elements
    ]
