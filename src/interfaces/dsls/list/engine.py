from interfaces.dsls.list import parse
from interfaces.dsls.shared import lexing, evaluating


def eval(s: str) -> list[str]:
    toks = lexing.lex(s, multiline_strings=False)
    ast = parse.parse(toks)
    return [evaluating.get_string_from_text_node(elem) for elem in ast.elements]
