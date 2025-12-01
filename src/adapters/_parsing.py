import ast
import typing as t
from types import MappingProxyType

from discord_.errors import FeedbackError
from structures.attribute import AnyAttributeT, BaseAttribute
from structures.attribute.slot_str import SlotTypeT
from structures.task.attribute_value_mapping import AttributeValueMapping
from utils import text
from utils.expression_parsing import errors as ep_errors
from utils.expression_parsing.parser import ExpressionParser, ExpressionParserConfig
from utils.expression_parsing.visitor import (
    BaseExpressionVisitor,
    ExpressionVisitorConfig,
)
from utils.text import NormStr

from . import errors

from ._parsing import utils_

type FilterAvmCollectionT = MappingProxyType[int, dict[NormStr, frozenset[SlotTypeT]]]
type FilterAttributesT = MappingProxyType[NormStr, AnyAttributeT]


_CHILD_TYPE_TO_STR: dict[type[ast.expr], str] = {
    ast.Constant: "string",
    ast.List: "list",
    ast.Tuple: "tuple",
    ast.Dict: "mapping"
}


_GENERAL_ERROR = FeedbackError(
    "Invalid Syntax Error",
    t"The entered syntax is invalid!"
)

def validate_children_type[T: ast.AST](
    children: t.Iterable[ast.AST], child_type: type[T]
) -> tuple[T, ...]:
    ch = tuple(children)

    if child_type is not ast.AST:
        for child in ch:
            if not isinstance(child, child_type):
                raise _GENERAL_ERROR

    return ch  # type: ignore


def visit_Constant_and_validate_str(
    node: ast.Constant, visitor: BaseExpressionVisitor
) -> str:
    if not isinstance(node.value, str):
        raise FeedbackError(
            "String Expected",
            t'Expected a value that represents a string (`"text wrapped in quotes"`), but received `{node.value}` instead!'
        )

    if len(node.value) > visitor.config.STR_LEN_MAX:
        raise FeedbackError(
            "String Length Hard Limit Reached",
            t"The string `{text.shorten(node.value)}` of length `{len(node.value)}` has surpassed the hard limit `{visitor.config.STR_LEN_MAX}`!"
        )

    return node.value


def visit_List_and_validate_children(
    node: ast.List, visitor: BaseExpressionVisitor, elts_type: type[ast.expr]
) -> list:
    elts = validate_children_type(node.elts, elts_type)
    return [visitor.visit(n) for n in elts]


def visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
    node: ast.Dict, visitor: BaseExpressionVisitor
) -> t.Any:
    if None in node.keys:
        raise _GENERAL_ERROR

    keys = t.cast(list[ast.AST], node.keys)
    values = node.values

    keys = validate_children_type(keys, ast.Constant)
    values = validate_children_type(values, ast.List)

    dct: dict = {}

    for k, v in zip(keys, values):
        k_value = visitor.visit(k)

        if k_value in dct:
            raise ValueError("Dict key not unique")

        dct[k_value] = visitor.visit(v)

    return dct


_KIBIBYTE = 2**10

_CONFIG_PARSER = ExpressionParserConfig(_KIBIBYTE * _KIBIBYTE * 2, _KIBIBYTE * 4)
_CONFIG_VISITOR = ExpressionVisitorConfig(255)


_OP_TO_FUNC: dict[
    type[ast.AST], t.Callable[[SlotTypeT, frozenset[SlotTypeT]], bool]
] = {
    ast.Eq: lambda v, tav: v in tav,
    ast.NotEq: lambda v, tav: v not in tav,
    ast.Lt: lambda v, tav: any(
        v < s for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.LtE: lambda v, tav: any(
        v <= s for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.Gt: lambda v, tav: any(
        v > s for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.GtE: lambda v, tav: any(
        v >= s for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
}


class FilterVisitor(
    BaseExpressionVisitor[
        list[AttributeValueMapping], [t.Iterable[AttributeValueMapping]]
    ],
    body_type=(ast.BoolOp, ast.Compare),
):
    def start_visit(
        self, node: ast.AST, avms: t.Iterable[AttributeValueMapping]
    ) -> list[AttributeValueMapping]:
        attribute_value_mappings: dict[int, AttributeValueMapping] = {
            id(avm): avm for avm in avms
        }

        favmc: FilterAvmCollectionT = MappingProxyType(
            {
                id(avm): {
                    attr.norm_name: frozenset(map(attr.slot_type, val))
                    for attr, val in avm.combined.items()
                }
                for avm in attribute_value_mappings.values()
            }
        )

        attributes: FilterAttributesT = MappingProxyType(
            {
                attr.norm_name: attr
                for avm in attribute_value_mappings.values()
                for attr in avm.combined
            }
        )

        result: FilterAvmCollectionT = super().visit(node, favmc, attributes)

        return list(attribute_value_mappings[id] for id in result)

    def visit_BoolOp(
        self,
        node: ast.BoolOp,
        favmc: FilterAvmCollectionT,
        attributes: FilterAttributesT,
    ) -> t.Any:
        assert isinstance(node.op, ast.And | ast.Or)

        values = validate_children_type(node.values, ast.Compare)

        if isinstance(node.op, ast.Or):
            remaining = favmc
            result: dict[int, dict[NormStr, frozenset[SlotTypeT]]] = {}

            for v in values:
                if not remaining:
                    break

                new: FilterAvmCollectionT = self.visit(v, remaining, attributes)
                remaining = dict(remaining.items() - new.items())
                result |= new

            return result

        if isinstance(node.op, ast.And):
            for v in values:
                if not favmc:
                    break

                new: FilterAvmCollectionT = self.visit(v, favmc, attributes)
                favmc = MappingProxyType(dict(favmc.items() & new.items()))

            return favmc

        t.assert_never(node.op)

    def visit_Compare(
        self,
        node: ast.Compare,
        favmc: FilterAvmCollectionT,
        attributes: FilterAttributesT,
    ) -> t.Any:
        if len(node.ops) > 1:
            raise ep_errors.WrongVisitError(node.ops[1], None)

        op = node.ops[0]

        op_func = _OP_TO_FUNC.get(op.__class__)

        if op_func is None:
            raise FeedbackError(
                "Invalid Comparison",
                t"The comparison"
            )

        left, right = node.left, node.comparators[0]

        LEFT_RIGHT_TYPE = ast.Constant

        if not isinstance(left, LEFT_RIGHT_TYPE):
            raise ep_errors.WrongVisitError(left, LEFT_RIGHT_TYPE)

        if not isinstance(right, LEFT_RIGHT_TYPE):
            raise ep_errors.WrongVisitError(right, LEFT_RIGHT_TYPE)

        attr_name: NormStr = self.visit(right, None)
        attr = attributes.get(attr_name)

        if attr is None:
            raise errors.StructureNotFoundViaSynFeedbackError(
                attr_name, BaseAttribute, False
            )

        value: SlotTypeT = self.visit(left, attr)

        return MappingProxyType(
            {i: tav for i, tav in favmc.items() if op_func(value, tav[attr_name])}
        )

    def visit_Constant(
        self, node: ast.Constant, attribute: AnyAttributeT | None
    ) -> t.Any:
        c = utils_.visit_Constant_and_validate_str(node, self)

        if attribute is None:
            return c

        return attribute.slot_type(c)


FILTER_PARSER = ExpressionParser(
    FilterVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER
)




class ListOfStrVisitor(BaseExpressionVisitor[list[str], []], body_type=ast.List):
    def start_visit(self, node: ast.AST) -> list[str]:
        return self.visit(node)

    def visit_List(self, node: ast.List) -> t.Any:
        return utils_.visit_List_and_validate_children(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils_.visit_Constant_and_validate_str(node, self)


class ListOfTupleVisitor[T: tuple](
    BaseExpressionVisitor[list[T], []], body_type=ast.List
):
    def start_visit(self, node: ast.AST) -> list[T]:
        return self.visit(node)

    def __init__(
        self,
        handle_tuple: t.Callable[[ast.Tuple, t.Self], T],
        *,
        config: ExpressionVisitorConfig,
    ) -> None:
        self._handle_tuple = handle_tuple
        super().__init__(config=config)

    def visit_List(self, node: ast.List) -> t.Any:
        return utils_.visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)


class DictOfStrToListOfStrVisitor(
    BaseExpressionVisitor[dict[str, list[str]], []], body_type=ast.Dict
):
    def start_visit(self, node: ast.AST) -> dict[str, list[str]]:
        return self.visit(node)

    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return (
            utils_.visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
                node, self
            )
        )

    def visit_List(self, node: ast.List) -> t.Any:
        return utils_.visit_List_and_validate_children(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils_.visit_Constant_and_validate_str(node, self)


class DictOfStrToListOfTupleVisitor[T: tuple](
    BaseExpressionVisitor[dict[str, list[T]], []], body_type=ast.Dict
):
    def start_visit(self, node: ast.AST) -> dict[str, list[T]]:
        return self.visit(node)

    def __init__(
        self,
        handle_tuple: t.Callable[[ast.Tuple, t.Self], T],
        *,
        config: ExpressionVisitorConfig,
    ) -> None:
        self._handle_tuple = handle_tuple
        super().__init__(config=config)

    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return (
            utils_.visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
                node, self
            )
        )

    def visit_List(self, node: ast.List) -> t.Any:
        return utils_.visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils_.visit_Constant_and_validate_str(node, self)

LIST_PARSER = ExpressionParser(
    ListOfStrVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER
)
MAPPING_PARSER = ExpressionParser(
    DictOfStrToListOfStrVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER
)


def _handle_name_aliases_tuple(
    tup: ast.Tuple, visitor: ListOfTupleVisitor
) -> tuple[str, list[str]]:
    if len(tup.elts) != 2:
        raise errors.InvalidArgumentFeedbackError(
            t"A specified tuple that must be of length **2** has the length **{len(tup.elts)}**!"
        )

    first, second = tup.elts

    if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
        raise errors.InvalidArgumentFeedbackError(
            t"The first element of a specified tuple is not a string, when it should be!"
        )

    elts: list[str] = []
    valid: bool = True

    if not isinstance(second, ast.List):
        valid = False
    else:
        for elem in second.elts:
            if not isinstance(elem, ast.Constant) or not isinstance(elem.value, str):
                valid = False
                break

            elts.append(elem.value)

    if not valid:
        raise errors.InvalidArgumentFeedbackError(
            t"The second element of a tuple is not a list of strings, when it should be!"
        )

    return (first.value, elts)


LIST_OF_NAME_ALIASES_PARSER = ExpressionParser(
    ListOfTupleVisitor(_handle_name_aliases_tuple, config=_CONFIG_VISITOR),
    config=_CONFIG_PARSER,
)