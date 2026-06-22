from interfaces.dsl.shared import lex, parsing
from interfaces.dsl.value_list import parse

def eval(s: str) -> list[str]:
    toks = lex.lex(s, multiline=False)
    ast = parse.parse(toks)
    return [parsing.get_string_from_stringy_node(elem) for elem in ast.elements]