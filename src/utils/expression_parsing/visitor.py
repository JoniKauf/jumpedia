import ast
import typing as t

from . import errors
from . import utils

class ExpressionVisitorConfig(t.NamedTuple):
    STR_LEN_MAX: int

class BaseExpressionVisitor[T](ast.NodeVisitor):
    def __init__(self, *, config: ExpressionVisitorConfig) -> None:
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

class ListOfStrVisitor(BaseExpressionVisitor[list[str]], body_type=ast.List):
    def visit_List(self, node: ast.List) -> t.Any:
        return utils.visit_List_and_validate_children(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils.visit_Constant_str_and_validate_value(node, self)


class ListOfTupleVisitor[T: tuple](BaseExpressionVisitor[list[T]], body_type=ast.List):
    def __init__(self, handle_tuple: t.Callable[[ast.Tuple, t.Self], T], *, config: ExpressionVisitorConfig) -> None:
        self._handle_tuple = handle_tuple
        super().__init__(config=config)
    
    def visit_List(self, node: ast.List) -> t.Any:
        return utils.visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)


class DictOfStrToListOfStrVisitor(BaseExpressionVisitor[dict[str, list[str]]], body_type=ast.Dict):
    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return utils.visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(node, self)

    def visit_List(self, node: ast.List) -> t.Any:
        return utils.visit_List_and_validate_children(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils.visit_Constant_str_and_validate_value(node, self)


class DictOfStrToListOfTupleVisitor[T: tuple](BaseExpressionVisitor[dict[str, list[T]]], body_type=ast.Dict):
    def __init__(self, handle_tuple: t.Callable[[ast.Tuple, t.Self], T], *, config: ExpressionVisitorConfig) -> None:
        self._handle_tuple = handle_tuple
        super().__init__(config=config)

    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return utils.visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(node, self)

    def visit_List(self, node: ast.List) -> t.Any:
        return utils.visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)
    
    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils.visit_Constant_str_and_validate_value(node, self)