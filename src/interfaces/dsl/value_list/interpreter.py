from interfaces.dsl.shared.lexer import Lexer
from interfaces.dsl.value_list.evaluator import ValueListEvaluator
from interfaces.dsl.value_list.transformer import ValueListTransformer


class ValueListInterpreter:
    def interpret(self, s: str) -> list[str]:
        toks = Lexer(multiline=False).lex(s)
        ast = ValueListTransformer().transform(toks)
        res = ValueListEvaluator().evaluate(ast)
        return res
