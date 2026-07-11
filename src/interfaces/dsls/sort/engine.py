from interfaces.dsls.core.engine import BaseEngine
from interfaces.dsls.core.lex import Lexer
from interfaces.dsls.sort.parse import SortParser



class SortEngine(BaseEngine):
    def eval(self, s: str) -> list[tuple[str, bool]]:
        toks = Lexer(multiline_strings=False).lex(s)
        ast = SortParser(s).parse(toks)
        return [
            (self.get_string_from_text_node(elem.value), elem.asc)
            for elem in ast.elements
        ]