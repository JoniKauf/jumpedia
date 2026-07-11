from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.filter import AndFilter, OrFilter, ComparisonFilter, Filter, OpType, EMPTY
from interfaces.dsls.expression.parse import ExpressionParser
from interfaces.dsls.shared.engine import BaseEngine
from interfaces.dsls.shared.errors.parse import UnexpectedToken
from interfaces.dsls.shared.lex import Lexer
from interfaces.dsls.shared.parse import ExprNode, TextNodeT
import typing as t
from interfaces.dsls.expression import parse


class FilterEngine(BaseEngine):
    def eval(self, s: str) -> Filter:
        toks = Lexer(multiline_strings=False).lex(s)
        ast = ExpressionParser(s, 16).parse(toks)
        return self._eval_recursively(ast)
        
    def _eval_recursively(self, node: ExprNode) -> Filter:
        match node:
            case parse.BoolOp() as bool_op:
                elems = tuple(_eval_recursively(elem) for elem in bool_op.elements)

                match bool_op.type:
                    case parse.BoolOpType.OR:
                        return OrFilter(elems)
                    case parse.BoolOpType.AND:
                        return AndFilter(elems)

                t.assert_never(bool_op)

            case parse.BinOp() as bin_op:
                left = _eval_recursively(bin_op.left)

                if not isinstance(left, TextNodeT):
                    raise UnexpectedToken()
                right = _eval_recursively(bin_op.right)

                return ComparisonFilter(
                    AttributeSynStr(left)
                )
