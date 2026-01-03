import ast
import functools
import typing as t
from types import EllipsisType

from discord_.errors import FeedbackError
from structures.attribute import AnyAttributeT, BaseAttribute
from structures.attribute.collection import Collection
from structures.attribute.slot_str import SlotTypeT
from structures.errors import CollectionEntryNotFoundError
from structures.task import Task
from structures.task.attribute_value_mapping import (
    AnyAttributeValueMappingT,
    AttributeValueMapping,
    UserAttributeValueMapping,
)
from utils import text
from utils.expression_parsing import errors as ep_errors
from utils.expression_parsing.parser import ExpressionParser, ExpressionParserConfig
from utils.expression_parsing.visitor import (
    BaseExpressionVisitor,
    ExpressionVisitorConfig,
)
from utils.text import NormStr, RealStr

from . import errors

type FilterAvmCollectionT = dict[int, dict[NormStr, frozenset[SlotTypeT]]]
type FilterAttributesT = dict[NormStr, AnyAttributeT]


_CHILD_TYPE_TO_STR: dict[type[ast.expr], str] = {
    ast.Constant: "string",
    ast.List: "list",
    ast.Tuple: "tuple",
    ast.Dict: "mapping",
}


def validate_children_type[T: ast.AST](
    children: t.Iterable[ast.AST], child_type: type[T] | tuple[type[T], ...]
) -> tuple[T, ...]:
    ch = tuple(children)

    if child_type is not ast.AST:
        for child in ch:
            if not isinstance(child, child_type):
                raise TypeError(child, child_type)

    return ch  # type: ignore


def visit_Constant_and_validate_str(
    node: ast.Constant, visitor: BaseExpressionVisitor
) -> str:
    if not isinstance(node.value, str):
        raise FeedbackError(
            "String Expected",
            t'Expected a value that represents a string (`"text wrapped in quotes"`), but received `{node.value}` instead!',
        )

    if len(node.value) > visitor.config.STR_LEN_MAX:
        raise FeedbackError(
            "String Length Hard Limit Reached",
            t"The string `{text.shorten(node.value)}` of length `{len(node.value)}` has surpassed the hard limit `{visitor.config.STR_LEN_MAX}`!",
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
        raise ep_errors.WrongVisitError(None, None)

    keys = t.cast(list[ast.AST], node.keys)
    values = node.values

    keys = validate_children_type(keys, ast.Constant)
    values = validate_children_type(values, ast.List)

    dct: dict = {}

    for k, v in zip(keys, values):
        k_value = visitor.visit(k)

        if k_value in dct:
            raise FeedbackError(
                "Not Unique Key Error",
                t"The key `{k_value}` was specified multiple times in a mapping!",
            )

        dct[k_value] = visitor.visit(v)

    return dct


_KIBIBYTE = 2**10

_CONFIG_PARSER = ExpressionParserConfig(_KIBIBYTE * _KIBIBYTE * 2, _KIBIBYTE * 4)
_CONFIG_VISITOR = ExpressionVisitorConfig(255)


_OP_TO_FUNC: t.Final[
    dict[type[ast.AST], t.Callable[[frozenset[SlotTypeT], SlotTypeT], bool]]
] = {
    ast.Is: lambda tav, v: v in tav,
    ast.IsNot: lambda tav, v: v not in tav,
    ast.Lt: lambda tav, v: any(
        s < v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.LtE: lambda tav, v: any(
        s <= v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.Gt: lambda tav, v: any(
        s > v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
    ast.GtE: lambda tav, v: any(
        s >= v for s in tav  # pyright: ignore[reportOperatorIssue]
    ),
}

_ORDER_OPS: t.Final[frozenset[type[ast.AST]]] = frozenset(
    (ast.Lt, ast.LtE, ast.Gt, ast.GtE)
)


class FilterVisitor[T: AttributeValueMapping | UserAttributeValueMapping](
    BaseExpressionVisitor[
        list[T],
        [t.Iterable[T], dict[NormStr, AnyAttributeT], set[AnyAttributeT]],
    ],
    body_type=(ast.BoolOp, ast.Compare),
):
    def start_visit(
        self,
        node: ast.AST,
        avms: t.Iterable[T],
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ) -> list[T]:
        attribute_value_mappings: dict[int, T] = {id(avm): avm for avm in avms}

        favmc: FilterAvmCollectionT = {
            id(avm): {
                attr.norm_name: frozenset(attr.slot_type(NormStr(slot)) for slot in val)
                for attr, val in avm.combined.items()
            }
            for avm in attribute_value_mappings.values()
        }

        result: FilterAvmCollectionT = super().visit(
            node, favmc, attributes, used_attributes
        )

        return list(attribute_value_mappings[id] for id in result)

    def visit_BoolOp(
        self,
        node: ast.BoolOp,
        favmc: FilterAvmCollectionT,
        attributes: FilterAttributesT,
        used_attributes: set[AnyAttributeT],
    ) -> t.Any:
        assert isinstance(node.op, ast.And | ast.Or)

        values = validate_children_type(node.values, (ast.Compare, ast.BoolOp))

        favmc = favmc.copy()

        if isinstance(node.op, ast.Or):
            remaining_to_check = favmc
            result: dict[int, dict[NormStr, frozenset[SlotTypeT]]] = {}

            for v in values:
                if not remaining_to_check:
                    break

                checked_successfully: FilterAvmCollectionT = self.visit(
                    v, remaining_to_check, attributes, used_attributes
                )

                for k in checked_successfully:
                    remaining_to_check.pop(k, None)

                result |= checked_successfully

            return result

        if isinstance(node.op, ast.And):
            for v in values:
                if not favmc:
                    break

                checked_successfully: FilterAvmCollectionT = self.visit(
                    v, favmc, attributes, used_attributes
                )
                favmc = {k: v for k, v in favmc.items() if k in checked_successfully}

            return favmc

        t.assert_never(node.op)

    def visit_Compare(
        self,
        node: ast.Compare,
        favmc: FilterAvmCollectionT,
        attributes: FilterAttributesT,
        used_attributes: set[AnyAttributeT],
    ) -> t.Any:
        if len(node.ops) > 1:
            raise ep_errors.WrongVisitError(node.ops[1], None)

        op = node.ops[0]

        op_func = _OP_TO_FUNC.get(op.__class__)

        if op_func is None:
            raise ep_errors.WrongVisitError(op_func, tuple(_OP_TO_FUNC))

        left, right = node.left, node.comparators[0]

        LEFT_RIGHT_TYPE = (ast.Constant, ast.Name)

        if not isinstance(left, LEFT_RIGHT_TYPE):
            raise ep_errors.WrongVisitError(left, LEFT_RIGHT_TYPE)

        if not isinstance(right, LEFT_RIGHT_TYPE):
            raise ep_errors.WrongVisitError(right, LEFT_RIGHT_TYPE)

        attr_syn: NormStr = self.visit(left, True, op)
        attr = attributes.get(attr_syn)

        if attr is None:
            raise errors.StructureNotFoundViaSynFeedbackError(
                attr_syn, BaseAttribute, False
            )

        used_attributes.add(attr)

        value_str_real: RealStr | EllipsisType = self.visit(right, False, op)
        value_str = NormStr(value_str_real)

        attr_name: NormStr = attr.norm_name

        if value_str is Ellipsis:
            MUST_BE_EMPTY = isinstance(op, ast.Is)

            return {
                i: tav
                for i, tav in favmc.items()
                if (not tav.get(attr_name)) is MUST_BE_EMPTY
            }

        collection = attr.get_collection()

        if collection:
            try:
                entry = collection.get_entry_by_syn(value_str)
            except KeyError:
                raise errors.CollectionEntryNotFoundFeedbackError(
                    CollectionEntryNotFoundError(value_str_real, collection)
                )

            return {
                i: tav
                for i, tav in favmc.items()
                if op_func(
                    frozenset(
                        collection.get_entry_by_syn(slot).collection_index
                        for slot in tav.get(attr_name, frozenset())
                    ),
                    entry.collection_index,
                )
            }

        value = attr.slot_type(value_str)

        return {
            i: tav
            for i, tav in favmc.items()
            if op_func(tav.get(attr_name, frozenset()), value)
        }

    def visit_Name(self, node: ast.Name, attr: bool, op: ast.cmpop) -> t.Any:
        return self.visit_Constant(ast.Constant(node.id), attr, op)

    def visit_Constant(self, node: ast.Constant, attr: bool, op: ast.cmpop) -> t.Any:
        if not attr and op not in _ORDER_OPS and node.value is Ellipsis:
            return node.value

        return RealStr(visit_Constant_and_validate_str(node, self))


class SortVisitor[T: AttributeValueMapping | UserAttributeValueMapping](
    BaseExpressionVisitor[
        list[T], [t.Iterable[T], dict[NormStr, AnyAttributeT], set[AnyAttributeT]]
    ],
    body_type=(ast.UnaryOp, ast.BinOp),
):
    def start_visit(
        self,
        node: ast.AST,
        avms: t.Iterable[T],
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ) -> list[T]:
        assert isinstance(node, ast.Expression)

        sorts: tuple[tuple[AnyAttributeT, bool], ...] = self.visit(
            node, attributes, used_attributes
        )

        attr_to_coll: dict[AnyAttributeT, Collection] = {
            attr: attr.get_collection() for attr, _ in sorts
        }
        task_to_sort_value: dict[Task, list[tuple[t.Any, ...]]] = {}

        for avm in avms:
            result: list[tuple[t.Any, ...]] = []

            for attr, _ in sorts:
                coll = attr_to_coll[attr]

                if coll:
                    result.append(
                        tuple(
                            coll.get_entry_by_syn(NormStr(slot)).id
                            for slot in avm.combined.get(attr, ())
                        )
                    )
                else:
                    result.append(
                        tuple(
                            attr.slot_type(NormStr(slot))
                            for slot in avm.combined.get(attr)
                        )
                    )

            task_to_sort_value[avm.task] = result

        def cmp_key(a: T, b: T) -> int:
            values_a = task_to_sort_value[a.task]
            values_b = task_to_sort_value[b.task]

            for va, vb, (_, asc) in zip(values_a, values_b, sorts):
                if va < vb:
                    return -1 if asc else 1

                if va > vb:
                    return 1 if asc else -1

            return 0

        return sorted(avms, key=functools.cmp_to_key(cmp_key))  # type: ignore

    def visit_UnaryOp(
        self,
        node: ast.UnaryOp,
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ):
        if not isinstance(node.op, ast.USub | ast.UAdd):
            raise ep_errors.WrongVisitError(node, ast.USub)

        if not isinstance(node.operand, ast.Name | ast.Constant):
            raise ep_errors.WrongVisitError(node, (ast.Name, ast.Constant))

        return (
            (
                self.visit(node.operand, attributes, used_attributes),
                isinstance(node.op, ast.UAdd),
            ),
        )

    def visit_BinOp(
        self,
        node: ast.BinOp,
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ):
        if not isinstance(node.left, ast.BinOp | ast.UnaryOp):
            raise ep_errors.WrongVisitError(node, (ast.BinOp, ast.UnaryOp))

        if not isinstance(node.op, ast.Sub | ast.Add):
            raise ep_errors.WrongVisitError(node, ast.USub)

        if not isinstance(node.right, ast.Name | ast.Constant):
            raise ep_errors.WrongVisitError(node, ast.BinOp)

        return (
            *self.visit(node.left, attributes, used_attributes),
            (
                self.visit(node.right, attributes, used_attributes),
                isinstance(node.op, ast.Add),
            ),
        )

    def visit_Name(
        self,
        node: ast.Name,
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ) -> t.Any:
        return self.visit_Constant(ast.Constant(node.id), attributes, used_attributes)

    def visit_Constant(
        self,
        node: ast.Constant,
        attributes: dict[NormStr, AnyAttributeT],
        used_attributes: set[AnyAttributeT],
    ) -> t.Any:
        attr_syn = NormStr(visit_Constant_and_validate_str(node, self))
        attr = attributes.get(attr_syn)

        if not attr:
            raise errors.StructureNotFoundViaSynFeedbackError(
                attr_syn, BaseAttribute, False
            )

        used_attributes.add(attr)

        return attr


FILTER_PARSER = ExpressionParser(
    FilterVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER
)

SORT_VISITOR = ExpressionParser(
    SortVisitor(config=_CONFIG_VISITOR), config=_CONFIG_PARSER
)


class ListOfStrVisitor(BaseExpressionVisitor[list[str], []], body_type=ast.List):
    def start_visit(self, node: ast.AST) -> list[str]:
        return self.visit(node)

    def visit_List(self, node: ast.List) -> t.Any:
        return visit_List_and_validate_children(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return visit_Constant_and_validate_str(node, self)


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
        return visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)


class DictOfStrToListOfStrVisitor(
    BaseExpressionVisitor[dict[str, list[str]], []], body_type=ast.Dict
):
    def start_visit(self, node: ast.AST) -> dict[str, list[str]]:
        return self.visit(node)

    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
            node, self
        )

    def visit_List(self, node: ast.List) -> t.Any:
        return visit_List_and_validate_children(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return visit_Constant_and_validate_str(node, self)


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
        return visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
            node, self
        )

    def visit_List(self, node: ast.List) -> t.Any:
        return visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return visit_Constant_and_validate_str(node, self)


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
