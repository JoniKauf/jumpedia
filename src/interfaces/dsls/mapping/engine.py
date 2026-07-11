import typing as t

from interfaces.dsls.mapping.parse import MappingParser
from interfaces.dsls.core.engine import BaseEngine
from interfaces.dsls.core.lex import Lexer


class MappingEngine(BaseEngine):
    def eval(self, s: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
        toks = Lexer(multiline_strings=False).lex(s)
        ast = MappingParser(s).parse(toks)

        return tuple(
            (
                self.get_string_from_text_node(item.key),
                tuple(
                    self.get_string_from_text_node(elem)
                    for elem in item.value.elements
                ),
            )
            for item in ast.items
        )
