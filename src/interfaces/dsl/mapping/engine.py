from interfaces.dsl.mapping import parse
from interfaces.dsl.shared import lex, parsing


def eval(s: str) -> dict[str, list[str]]:
    toks = lex.lex(s, multiline_strings=False)
    ast = parse.parse(toks)

    return {
        parsing.get_string_from_text_node(item.key): [
            parsing.get_string_from_text_node(elem) for elem in item.value.elements
        ]
        for item in ast.items
    }
