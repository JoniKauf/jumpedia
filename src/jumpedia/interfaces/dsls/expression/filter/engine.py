import logging
import typing as t

from jumpedia.domain.value_objects.filter import (
    AndFilter,
    EmptyComparisonFilter,
    FilterT,
    NonEmptyComparisonFilter,
    OpType,
    OrFilter,
)
from jumpedia.interfaces.dsls.core.engine import BaseEngine
from jumpedia.interfaces.dsls.core.errors.eval import (
    EmptyAfterNonEqualityOperator,
    UnexpectedBinOp,
    UnexpectedNode,
)
from jumpedia.interfaces.dsls.core.lex import Lexer
from jumpedia.interfaces.dsls.core.parse import (
    TEXT_NODE_TYPES,
    ExprNode,
    IdentifierNode,
)
from jumpedia.interfaces.dsls.expression import parse
from jumpedia.interfaces.dsls.expression.parse import BinOpType, ExpressionParser

logger = logging.getLogger(__name__)


class FilterEngine(BaseEngine):
    def __init__(self) -> None:
        super().__init__()
        self._s: str | None = None

    def eval(self, s: str) -> FilterT:
        logger.info(f"--- {self.eval.__qualname__} ---")
        logger.info("Lexing...")
        toks = Lexer(multiline_strings=False).lex(s)

        logger.info("Parsing...")
        ast = ExpressionParser(s, 16).parse(toks)

        self._s = s

        try:
            logger.info("Evaluating...")
            return self._eval_recursively(ast)
        finally:
            self._s = None

    def _eval_recursively(self, node: ExprNode) -> FilterT:
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
                        raise UnexpectedBinOp(
                            self._s,
                            (
                                BinOpType.IS,
                                BinOpType.IS_NOT,
                                BinOpType.LT,
                                BinOpType.LTE,
                                BinOpType.GT,
                                BinOpType.GTE,
                            ),
                            bin_op,
                        )

                if not isinstance(bin_op.right, TEXT_NODE_TYPES):
                    assert self._s is not None
                    raise UnexpectedNode(self._s, TEXT_NODE_TYPES, bin_op.left)

                if not isinstance(bin_op.left, TEXT_NODE_TYPES):
                    assert self._s is not None
                    raise UnexpectedNode(self._s, TEXT_NODE_TYPES, bin_op.left)

                attr = self.get_string_from_text_node(bin_op.left)

                if (
                    isinstance(bin_op.right, IdentifierNode)
                    and bin_op.right.name == "_"
                ):
                    if op_type not in (OpType.EQ, OpType.NEQ):
                        assert self._s is not None
                        raise EmptyAfterNonEqualityOperator(self._s, bin_op)

                    return EmptyComparisonFilter(attr, op_type)

                return NonEmptyComparisonFilter(
                    attr, op_type, self.get_string_from_text_node(bin_op.right)
                )

            case _:
                assert self._s is not None
                raise UnexpectedNode(self._s, (parse.BoolOp, parse.BinOp), node)
