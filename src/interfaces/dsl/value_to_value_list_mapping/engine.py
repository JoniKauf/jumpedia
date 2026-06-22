from interfaces.dsl.shared import lex, parsing
from interfaces.dsl.value_to_value_list_mapping import parse

def eval( s: str) -> dict[str, list[str]]:
    toks = lex.lex(s, multiline=False)
    ast = parse.parse(toks)

    return {
        parsing.get_string_from_stringy_node(item.key): [
            parsing.get_string_from_stringy_node(elem) for elem in item.value.elements
        ]
        for item in ast.items
    }
