from interfaces.dsls.simple_list import parse
from interfaces.dsls.shared import lex, parsing


def eval(s: str) -> list[str]:
    toks = lex.lex(s, multiline_strings=False)
    ast = parse.parse(toks)
    return [parsing.get_string_from_text_node(elem) for elem in ast.elements]
