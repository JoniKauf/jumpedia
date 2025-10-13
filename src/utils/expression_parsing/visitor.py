import ast
import typing as t

from . import errors
from .config import ExpressionParsingConfig


class BaseExpressionVisitor[T](ast.NodeVisitor):
    def __init__(self, config: ExpressionParsingConfig) -> None:
        if self.__class__ is BaseExpressionVisitor:
            raise RuntimeError

        self.config = config

        super().__init__()

    def __init_subclass__(cls, body_type: type[ast.AST]) -> None:
        cls._body_type = body_type
        super().__init_subclass__()

    def start_visit(self, node: ast.AST) -> T:
        return self.visit(node)

    def visit_Expression(self, node: ast.Expression) -> t.Any:
        if not isinstance(node.body, self.__class__._body_type):
            raise errors.WrongChildError(node.body, self.__class__._body_type)

        return self.visit(node.body)

    def generic_visit(self, node: ast.AST) -> t.Any:
        raise errors.GenericVisitError(node)


def _check_children_type[T: ast.AST](
    children: t.Iterable[ast.AST], child_type: type[T]
) -> list[T]:
    if child_type is not ast.AST:
        for child in children:
            if not isinstance(child, child_type):
                raise errors.WrongChildError(child, child_type)

    return list(children)  # type: ignore


def _typical_visit_Constant(node: ast.Constant, visitor: BaseExpressionVisitor) -> str:
    if not isinstance(node.value, str):
        raise errors.NotStrConstantError(node.value)

    if len(node.value) > visitor.config.STR_LEN_MAX:
        raise errors.MaxStringLengthExceededError()

    return node.value


def _typical_visit_List(
    node: ast.List, visitor: BaseExpressionVisitor, elts_type: type[ast.AST]
) -> list:
    elts = _check_children_type(node.elts, elts_type)
    return [visitor.visit(n) for n in elts]


def _typical_visit_Dict(node: ast.Dict, visitor: BaseExpressionVisitor) -> t.Any:
    if None in node.keys:
        raise errors.BaseExpressionParsingError

    keys = t.cast(list[ast.AST], node.keys)
    values = node.values

    keys = _check_children_type(keys, ast.Constant)
    values = _check_children_type(values, ast.List)

    dct: dict = {}

    for k, v in zip(keys, values):
        kv = visitor.visit(k)

        if kv in dct:
            raise ValueError("Dict key not unique")

        dct[kv] = visitor.visit(v)

    return dct

class ListOfStrVisitor(BaseExpressionVisitor[list[str]], body_type=ast.List):
    def visit_List(self, node: ast.List) -> t.Any:
        return _typical_visit_List(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return _typical_visit_Constant(node, self)


class ListOfTupleVisitor[T: tuple](BaseExpressionVisitor[list[T]], body_type=ast.List):
    def __init__(self, handle_tuple: t.Callable[[ast.Tuple, t.Self], T], config: ExpressionParsingConfig) -> None:
        self._handle_tuple = handle_tuple
        super().__init__(config)
    
    def visit_List(self, node: ast.List) -> t.Any:
        return _typical_visit_List(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)


class DictOfStrToListOfStrVisitor(BaseExpressionVisitor[dict[str, list[str]]], body_type=ast.Dict):
    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return _typical_visit_Dict(node, self)

    def visit_List(self, node: ast.List) -> t.Any:
        return _typical_visit_List(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return _typical_visit_Constant(node, self)


class DictOfStrToListOfTupleVisitor[T: tuple](BaseExpressionVisitor[dict[str, list[T]]], body_type=ast.Dict):
    def __init__(self, handle_tuple: t.Callable[[ast.Tuple, t.Self], T], config: ExpressionParsingConfig) -> None:
        self._handle_tuple = handle_tuple
        super().__init__(config)

    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return _typical_visit_Dict(node, self)

    def visit_List(self, node: ast.List) -> t.Any:
        return _typical_visit_List(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)
    
    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return _typical_visit_Constant(node, self)