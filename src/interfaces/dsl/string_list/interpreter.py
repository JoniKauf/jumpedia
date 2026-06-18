from interfaces.dsl.shared.lexer import Lexer
from interfaces.dsl.string_list.evaluator import Evaluator
from interfaces.dsl.string_list.transformer import Transformer


class Interpreter:
    def interpret(self, s: str) -> list[str]:
        toks = Lexer(multiline=False).lex(s)
        ast = Transformer().transform(toks)
        res = Evaluator().evaluate(ast)
        return res
