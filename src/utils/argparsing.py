import ast
import io
import tokenize
import typing as t
from dataclasses import dataclass


class BaseExpressionParserVisitor[T](ast.NodeVisitor):
    def __init__(self) -> None:
        if self.__class__ is BaseExpressionParserVisitor:
            raise RuntimeError

        super().__init__()

    def __init_subclass__(cls, body_type: type[ast.AST]) -> None:
        cls._body_type = body_type
        super().__init_subclass__()

    def start_visit(self, node: ast.AST) -> T:
        return self.visit(node)

    def visit_Expression(self, node: ast.Expression) -> t.Any:
        if not isinstance(node.body, self.__class__._body_type):
            raise ValueError(
                f"Root is {node.body.__class__} instead of {self.__class__._body_type}"
            )

        return self.visit(node.body)

    def generic_visit(self, node: ast.AST) -> t.Any:
        # This should never be called because the parent should
        # check whether the children are of the correct type.
        assert False


def _check_children_type[T: ast.AST](
    children: t.Iterable[ast.AST], child_type: type[T]
) -> list[T]:
    if child_type is not ast.AST:
        for child in children:
            if not isinstance(child, child_type):
                raise ValueError(f"child is {child.__class__} instead of {child_type}")

    return list(children)  # type: ignore


def _typical_visit_Constant(node: ast.Constant) -> str:
    if not isinstance(node.value, str):
        raise ValueError(f"constant's value is {node.value.__class__} instead of {str}")

    return node.value


def _typical_visit_List(
    node: ast.List, visitor: BaseExpressionParserVisitor, elts_type: type[ast.AST]
) -> list:
    elts = _check_children_type(node.elts, elts_type)
    return [visitor.visit(n) for n in elts]


def _typical_visit_Dict(node: ast.Dict, visitor: BaseExpressionParserVisitor) -> t.Any:
    if None in node.keys:
        raise ValueError("Stars")

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


class TupleVisitorMixin[T: tuple]:
    def __init__(self, handle_tuple: t.Callable[[ast.Tuple, t.Self], T]) -> None:
        self._handle_tuple = handle_tuple
        super().__init__()

    def visit_Tuple(self, node: ast.Tuple) -> t.Any:
        return self._handle_tuple(node, self)
    

class ListOfStrVisitor(BaseExpressionParserVisitor[list[str]], body_type=ast.List):
    def visit_List(self, node: ast.List) -> t.Any:
        return _typical_visit_List(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return _typical_visit_Constant(node)

class ListOfTupleVisitor[T: tuple](TupleVisitorMixin[T], BaseExpressionParserVisitor[list[T]], body_type=ast.List):
    def visit_List(self, node: ast.List) -> t.Any:
        return _typical_visit_List(node, self, ast.Tuple)

class DictOfStrToListOfStrVisitor(
    BaseExpressionParserVisitor[dict[str, list[str]]], body_type=ast.Dict
):
    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return _typical_visit_Dict(node, self)

    def visit_List(self, node: ast.List) -> t.Any:
        return _typical_visit_List(node, self, ast.Constant)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return _typical_visit_Constant(node)


class DictOfStrToListOfTupleVisitor[T: tuple](
    TupleVisitorMixin[T], BaseExpressionParserVisitor[dict[str, list[T]]], body_type=ast.Dict
):
    def visit_Dict(self, node: ast.Dict) -> t.Any:
        return _typical_visit_Dict(node, self)

    def visit_List(self, node: ast.List) -> t.Any:
        return _typical_visit_List(node, self, ast.Tuple)

    def visit_Constant(self, node: ast.Constant) -> t.Any:
        return _typical_visit_Constant(node)


@dataclass(frozen=True, slots=True)
class ArgParser[T]:
    node_visitor: BaseExpressionParserVisitor[T]

    @staticmethod
    def _validate_tokens(s: str):
        tok_gen = tokenize.generate_tokens(io.StringIO(s).readline)
        prev_tok = next(tok_gen, None)

        if prev_tok is None:
            return

        for tok in tok_gen:
            # Disallow inplicit s
            if prev_tok.type == tokenize.STRING and tok.type == tokenize.STRING:
                raise ValueError("Implicit concat of strings")

            prev_tok = tok

    def parse(self, s: str) -> T:
        if not (s := s.strip()):
            raise ValueError("Empty string")

        # Throws TokenError when syntax wrong
        self.__class__._validate_tokens(s)

        return self.node_visitor.start_visit(ast.parse(s, mode="eval"))


def __main() -> None:
    clss = BaseExpressionParserVisitor.__subclasses__()

    def handle_tup(
        tup: ast.Tuple, visitor: BaseExpressionParserVisitor
    ) -> tuple[str, list[str]]:
        if len(tup.elts) != 2:
            raise ValueError("Tuple wrong amount of elements")

        first, second = tup.elts

        if not isinstance(first, ast.Constant):
            raise ValueError("First tuple element not constant")

        if not isinstance(second, ast.List):
            raise ValueError("Second tuple element not list")

        return (
            _typical_visit_Constant(first),
            _typical_visit_List(second, visitor, ast.Constant),
        )

    while True:
        inp = input(
            "\n".join(f"[{i}] {cls.__name__}" for i, cls in enumerate(clss)) + "\n> "
        )

        try:
            choice = int(inp)

            if not (0 <= choice < len(clss)):
                raise Exception
        except Exception:
            print("Invalid input!", end="\n\n\n")
            continue

        visitor_type = clss[choice]

        if visitor_type is not DictOfStrToListOfTupleVisitor:
            visitor = visitor_type()
        else:
            visitor = visitor_type(handle_tup)

        parser = ArgParser(visitor)

        while True:
            inp = input("Input: ")

            if inp == "exit":
                break

            try:
                print("Result:", repr(parser.parse(inp)))
            except ValueError as e:
                # raise e
                print("Error:", repr(e))

            print("\n")

        print("\n" * 5)


if __name__ == "__main__":
    __main()
