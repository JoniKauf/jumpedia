from interfaces.dsls.shared import evaluating, lexing
from interfaces.dsls.sort import parse


def eval(s: str) -> list[tuple[str, bool]]:
    toks = lexing.lex(s, multiline_strings=False)
    ast = parse.parse(toks, error_s=s)
    return [
        (evaluating.get_string_from_text_node(elem.value), elem.asc)
        for elem in ast.elements
    ]
