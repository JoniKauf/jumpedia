import ast
import types
import typing as t
from abc import ABC, abstractmethod

from . import errors


class ExpressionVisitorConfig(t.NamedTuple):
    STR_LEN_MAX: int


class BaseExpressionVisitor[T, **P]:
    def __init_subclass__(cls, body_type: type[ast.AST] | tuple[type[ast.AST], ...]) -> None:
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

