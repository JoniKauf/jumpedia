import typing as t

from interfaces.dsls.mapping import parse
from interfaces.dsls.shared import evaluating, lexing


def eval(s: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    toks = lexing.lex(s, multiline_strings=False)
    ast = parse.parse(toks, error_s=s)

    return tuple(
        (
            evaluating.get_string_from_text_node(item.key),
            tuple(
                evaluating.get_string_from_text_node(elem)
                for elem in item.value.elements
            ),
        )
        for item in ast.items
    )
