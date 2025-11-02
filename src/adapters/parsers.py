import ast
import typing as t
from types import MappingProxyType

from src.adapters.errors import (InvalidArgumentFeedbackError,
                                 StructureNotFoundViaSynFeedbackError)
from src.utils.expression_parsing import errors as ep_errors
from src.utils.expression_parsing import utils as ep_utils
from src.utils.expression_parsing.parser import (ExpressionParser,
                                                 ExpressionParserConfig)
from src.utils.expression_parsing.visitor import (BaseExpressionVisitor,
                                                  DictOfStrToListOfStrVisitor,
                                                  ExpressionVisitorConfig,
                                                  ListOfStrVisitor,
                                                  ListOfTupleVisitor)
from structures.attribute import AnyAttributeT, BaseAttribute
from src.structures.attribute.slot_str import SlotTypeT
from structures.task.attribute_value_mapping import AttributeValueMapping
from utils.text import NormStr

_KIBIBYTE = 2 ** 10

_CONFIG_PARSER = ExpressionParserConfig(_KIBIBYTE * _KIBIBYTE * 2, _KIBIBYTE * 4)
_CONFIG_VISITOR = ExpressionVisitorConfig(255)

LIST_PARSER = ExpressionParser(ListOfStrVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER)
MAPPING_PARSER = ExpressionParser(DictOfStrToListOfStrVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER)


def _handle_name_aliases_tuple(tup: ast.Tuple, visitor: ListOfTupleVisitor) -> tuple[str, list[str]]:
    ADDITIONAL = (
        t"The tuple should have 2 elements in this order:\n"
        t"1. The value (a string)\n"
        t"2. The aliases (a list of strings)"
    )

    if len(tup.elts) != 2:
        raise InvalidArgumentFeedbackError(
            t"A tuple of length {len(tup.elts)} is invalid!",
            additional=ADDITIONAL
        )
    
    first, second = tup.elts

    if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
        raise InvalidArgumentFeedbackError(
            t"The first element of the tuple is not a string!",
            additional=ADDITIONAL
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
        raise InvalidArgumentFeedbackError(
            t"The second element of the tuple is not a list of strings!",
            additional=ADDITIONAL
        )
    
    return (first.value, elts)

    
LIST_OF_NAME_ALIASES_PARSER = ExpressionParser(ListOfTupleVisitor(_handle_name_aliases_tuple, config=_CONFIG_VISITOR), config=_CONFIG_PARSER)

type FilterAvmCollectionT = MappingProxyType[int, dict[NormStr, frozenset[SlotTypeT]]]
type FilterAttributesT = MappingProxyType[NormStr, AnyAttributeT]



_OP_TO_FUNC: dict[type[ast.AST], t.Callable[[SlotTypeT, frozenset[SlotTypeT]], bool]] = {
    ast.Eq:    lambda v, tav: v in tav, 
    ast.NotEq: lambda v, tav: v not in tav, 
    ast.Lt:    lambda v, tav: any(v < s for s in tav),  # pyright: ignore[reportOperatorIssue]
    ast.LtE:   lambda v, tav: any(v <= s for s in tav), # pyright: ignore[reportOperatorIssue]
    ast.Gt:    lambda v, tav: any(v > s for s in tav),  # pyright: ignore[reportOperatorIssue]
    ast.GtE:   lambda v, tav: any(v >= s for s in tav)  # pyright: ignore[reportOperatorIssue]
}

class FilterVisitor(BaseExpressionVisitor[list[AttributeValueMapping], [t.Iterable[AttributeValueMapping]]], body_type=(ast.BoolOp, ast.Compare)):
    def start_visit(self, node: ast.AST, avms: t.Iterable[AttributeValueMapping]) -> list[AttributeValueMapping]:
        attribute_value_mappings: dict[int, AttributeValueMapping] = {
            avm.python_id: avm for avm in avms
        }

        favmc: FilterAvmCollectionT = MappingProxyType({
            avm.python_id: {
                attr.norm_name: frozenset(map(attr.slot_type.slot_to_norm, val))
                for attr, val in avm.combined.items()
            } for avm in attribute_value_mappings.values()
        })

        attributes: FilterAttributesT = MappingProxyType({
            attr.norm_name: attr
            for avm in attribute_value_mappings.values()
                for attr in avm.combined
        })

        result: FilterAvmCollectionT = super().visit(node, favmc, attributes)
        
        return list(attribute_value_mappings[id] for id in result)
    
    
    def visit_BoolOp(self, node: ast.BoolOp, favmc: FilterAvmCollectionT, attributes: FilterAttributesT) -> t.Any:
        assert isinstance(node.op, ast.And | ast.Or)

        values = ep_utils.validate_children_type(node.values, ast.Compare)

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

    def visit_Compare(self, node: ast.Compare, favmc: FilterAvmCollectionT, attributes: FilterAttributesT) -> t.Any:
        if len(node.ops) > 1:
            raise ep_errors.WrongVisitError(node.ops[1], None)
        
        op = node.ops[0]

        op_func = _OP_TO_FUNC.get(op.__class__)

        if op_func is None:
            raise ep_errors.WrongVisitError(op, self.__class__)
        
        left, right = node.left, node.comparators[0]
        
        LEFT_RIGHT_TYPE = ast.Constant

        if not isinstance(left, LEFT_RIGHT_TYPE):
            raise ep_errors.WrongVisitError(left, LEFT_RIGHT_TYPE)
        
        if not isinstance(right, LEFT_RIGHT_TYPE):
            raise ep_errors.WrongVisitError(right, LEFT_RIGHT_TYPE)

        attr_name: NormStr = self.visit(right, None)
        attr = attributes.get(attr_name)

        if attr is None:
            raise StructureNotFoundViaSynFeedbackError(attr_name, BaseAttribute)
        
        value: SlotTypeT = self.visit(left, attr)

        return MappingProxyType({
            i: tav 
            for i, tav in favmc.items()
            if op_func(value, tav[attr_name])
        })

    def visit_Constant(self, node: ast.Constant, attribute: AnyAttributeT | None) -> t.Any:
        c = ep_utils.visit_Constant_and_validate_str(node, self)

        if attribute is None:
            return c
        
        return attribute.slot_type.type(c)
    

FILTER_PARSER = ExpressionParser(
    FilterVisitor(config=_CONFIG_VISITOR),
    config=_CONFIG_PARSER
)