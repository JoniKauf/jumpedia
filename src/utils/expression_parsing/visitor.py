import ast
import types
import typing as t
from abc import ABC, abstractmethod

from . import errors, utils


class ExpressionVisitorConfig(t.NamedTuple):
    STR_LEN_MAX: int


class BaseExpressionVisitor[T, **P]:
    def __init_subclass__(cls, body_type: utils.ExpectedAstT[ast.AST]) -> None:
        cls._body_type = body_type
        super().__init_subclass__()

    def __init__(self, *, config: ExpressionVisitorConfig) -> None:
        if self.__class__ is BaseExpressionVisitor:
            raise RuntimeError

        self.config = config
        super().__init__()

    def start_visit(self, node: ast.AST, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.visit(node, *args, **kwargs)

    def visit(self, node: ast.AST, *args: t.Any, **kwargs: t.Any) -> t.Any:
        method = "visit_" + node.__class__.__name__
        visitor: t.Callable[t.Concatenate[ast.AST, P], t.Any] = getattr(
            self, method, self.generic_visit
        )
        return visitor(node, *args, **kwargs)

    def visit_Expression(
        self, node: ast.Expression, *args: t.Any, **kwargs: t.Any
    ) -> t.Any:
        if not isinstance(node.body, self.__class__._body_type):
            raise errors.WrongVisitError(node.body, self.__class__._body_type)

        return self.visit(node.body, *args, **kwargs)

    def generic_visit(self, node: ast.AST, *args: t.Any, **kwargs: t.Any) -> t.Any:
        raise errors.GenericVisitError(node)


class ListOfStrVisitor(BaseExpressionVisitor[list[str], []], body_type=ast.List):
    def start_visit(self, node: ast.AST) -> list[str]:
        return self.visit(node)

    def visit_List(self, node: ast.List) -> t.Any:
        return utils.visit_List_and_validate_children(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils.visit_Constant_and_validate_str(node, self)


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
        return utils.visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)


class DictOfStrToListOfStrVisitor(
    BaseExpressionVisitor[dict[str, list[str]], []], body_type=ast.Dict
):
    def start_visit(self, node: ast.AST) -> dict[str, list[str]]:
        return self.visit(node)

    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return (
            utils.visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
                node, self
            )
        )

    def visit_List(self, node: ast.List) -> t.Any:
        return utils.visit_List_and_validate_children(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils.visit_Constant_and_validate_str(node, self)


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
            utils.visit_Dict_and_validate_constant_to_list_and_no_star_and_unique_keys(
                node, self
            )
        )

    def visit_List(self, node: ast.List) -> t.Any:
        return utils.visit_List_and_validate_children(node, self, ast.Tuple)

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return utils.visit_Constant_and_validate_str(node, self)
