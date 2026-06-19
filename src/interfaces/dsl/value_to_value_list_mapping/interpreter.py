from interfaces.dsl.shared.lexer import Lexer
from interfaces.dsl.value_to_value_list_mapping.evaluator import (
    ValueToValueListMappingEvaluator,
)
from interfaces.dsl.value_to_value_list_mapping.transformer import (
    ValueToValueListMappingTransformer,
)


class ValueToValueListInterpreter:
    def interpret(self, s: str) -> dict[str, list[str]]:
        toks = Lexer(multiline=False).lex(s)
        ast = ValueToValueListMappingTransformer().transform(toks)
        res = ValueToValueListMappingEvaluator().evaluate(ast)
        return res
