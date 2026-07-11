from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from domain.value_objects.filter import AndFilter, OrFilter, ComparisonFilter, Filter, OpType, EMPTY
from interfaces.dsls.expression.parse import BinOpType, ExpressionParser
from interfaces.dsls.shared.engine import BaseEngine
from interfaces.dsls.shared.errors.eval import UnexpectedBinOp, UnexpectedNode
from interfaces.dsls.shared.lex import TEXT_TOKEN_TYPES, Lexer
from interfaces.dsls.shared.parse import TEXT_NODE_TYPES, ExprNode, IdentifierNode, TextNodeT
import typing as t
from interfaces.dsls.expression import parse


class FilterEngine(BaseEngine):
    def __init__(self) -> None:
        super().__init__()
        self._s = None

    def eval(self, s: str) -> Filter:
        toks = Lexer(multiline_strings=False).lex(s)
        ast = ExpressionParser(s, 16).parse(toks)

        self._s = s

        try:
            return self._eval_recursively(ast)
        finally:
            self._s = None

    def _eval_recursively(self, node: ExprNode) -> Filter:
        match node:
            case parse.BoolOp() as bool_op:
                elems = tuple(self._eval_recursively(elem) for elem in bool_op.elements)

                match bool_op.type:
                    case parse.BoolOpType.OR:
                        return OrFilter(elems)
                    case parse.BoolOpType.AND:
                        return AndFilter(elems)

                t.assert_never(bool_op)

            case parse.BinOp() as bin_op:
                op_type: OpType

                match bin_op.type:
                    case BinOpType.IS:
                        op_type = OpType.EQ
                    case BinOpType.IS_NOT:
                        op_type = OpType.NEQ
                    case BinOpType.LT:
                        op_type = OpType.LT
                    case BinOpType.LTE:
                        op_type = OpType.LTE
                    case BinOpType.GT:
                        op_type = OpType.GT
                    case BinOpType.GTE:
                        op_type = OpType.GTE
                    case _:
                        assert self._s is not None
                        raise UnexpectedBinOp(self._s, (BinOpType.IS, BinOpType.IS_NOT, BinOpType.LT, BinOpType.LTE, BinOpType.GT, BinOpType.GTE), bin_op.type)

                if not isinstance(bin_op.right, TEXT_NODE_TYPES):
                    assert self._s is not None
                    raise UnexpectedNode(self._s, TEXT_NODE_TYPES, bin_op.left)
                
                if not isinstance(bin_op.left, TEXT_NODE_TYPES):
                    assert self._s is not None
                    raise UnexpectedNode(self._s, TEXT_NODE_TYPES, bin_op.left)

                value: FieldSlotStr | EMPTY

                if not (isinstance(bin_op.right, IdentifierNode) and bin_op.right.name == '_'):
                    value = FieldSlotStr(self.get_string_from_text_node(bin_op.right))
                else:
                    if bin_op.type not in (BinOpType.IS, BinOpType.IS_NOT):
                        assert self._s is not None
                        raise UnexpectedNode(self._s, TEXT_NODE_TYPES, bin_op.right)

                    value = EMPTY

                return ComparisonFilter(
                    AttributeSynStr(self.get_string_from_text_node(bin_op.left)),
                    op_type,
                    value
                )
