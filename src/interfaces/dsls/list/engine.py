
from interfaces.dsls.list.parse import ListParser
from interfaces.dsls.shared.engine import BaseEngine
from interfaces.dsls.shared.lex import Lexer


class ListEngine(BaseEngine):
    def eval(self, s: str) -> list[str]:
        toks = Lexer(multiline_strings=False).lex(s)
        ast = ListParser(s).parse(toks)
        return [self.get_string_from_text_node(elem) for elem in ast.elements]
