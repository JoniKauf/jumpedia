import ast
import typing as t

from . import errors

if t.TYPE_CHECKING:
    from . import visitor

type ExpectedAstT[T: ast.AST] = type[T] | tuple[type[T], ...]


def validate_children_type[T: ast.AST](
    children: t.Iterable[ast.AST], child_type: type[T]
) -> tuple[T, ...]:
    ch = tuple(children)

    if child_type is not ast.AST:
        for child in ch:
            if not isinstance(child, child_type):
                raise errors.WrongVisitError(child, child_type)

    return ch  # type: ignore


def visit_Constant_and_validate_str(
    node: ast.Constant, visitor: visitor.BaseExpressionVisitor
) -> str:
    if not isinstance(node.value, str):
        raise errors.NotStrConstantError(node.value)

    if len(node.value) > visitor.config.STR_LEN_MAX:
        raise errors.MaxStringLengthExceededError()

    return node.value


def visit_List_and_validate_children(
    node: ast.List, visitor: visitor.BaseExpressionVisitor, elts_type: type[ast.AST]
) -> list:
    elts = validate_children_type(node.elts, elts_type)
    return [visitor.visit(n) for n in elts]


def visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
    node: ast.Dict, visitor: visitor.BaseExpressionVisitor
) -> t.Any:
    if None in node.keys:
        raise errors.BaseExpressionParsingError

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
