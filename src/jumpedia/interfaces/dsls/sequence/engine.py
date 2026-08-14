from jumpedia.interfaces.dsls.core.engine import BaseEngine
from jumpedia.interfaces.dsls.core.lex import Lexer
from jumpedia.interfaces.dsls.sequence.parse import SequenceParser


class SequenceEngine(BaseEngine):
    def eval(self, s: str) -> list[str]:
        toks = Lexer(multiline_strings=False).lex(s)
        ast = SequenceParser(s).parse(toks)
        return [self.get_string_from_text_node(elem) for elem in ast.elements]
