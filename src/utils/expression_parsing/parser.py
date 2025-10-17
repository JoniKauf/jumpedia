import ast
import io
import tokenize
from dataclasses import KW_ONLY, InitVar, dataclass
import typing as t

from . import errors
from .visitor import BaseExpressionVisitor, ExpressionVisitorConfig


class ExpressionParserConfig(t.NamedTuple):
    SOURCE_LEN_MAX: int
    TOKEN_COUNT_MAX: int


@dataclass(frozen=True, slots=True)
class ExpressionParser[T, **P]:
    visitor: BaseExpressionVisitor[T, P]
    _: KW_ONLY
    config: ExpressionParserConfig


    def _validate_tokens(self, s: str):
        tok_gen = tokenize.generate_tokens(io.StringIO(s).readline)
        prev_tok = next(tok_gen, None)

        if prev_tok is None:
            return

        if self.config.TOKEN_COUNT_MAX < 1:
            raise errors.MaxTokenCountExceecedError()

        count = 1

        for tok in tok_gen:
            count += 1

            if count > self.config.TOKEN_COUNT_MAX:
                raise errors.MaxTokenCountExceecedError()

            # Disallow inplicit string concat
            if prev_tok.type == tokenize.STRING and tok.type == tokenize.STRING:
                raise errors.ImplicitConcatOfStringsError(prev_tok.string, tok.string)

            prev_tok = tok

    def parse(self, s: str, *args: P.args, **kwargs: P.kwargs) -> T:
        if not (s := s.strip()):
            raise errors.EmptySrcError()

        if "\n" in s:
            raise errors.NewlineInSrcError()
        
        if len(s) > self.config.SOURCE_LEN_MAX:
            raise errors.MaxSrcLengthExceededError()

        # Throws TokenError when syntax wrong
        self._validate_tokens(s)

        return self.visitor.start_visit(ast.parse(s, mode="eval"), *args, **kwargs)


def __main():
    from .visitor import ListOfTupleVisitor, DictOfStrToListOfTupleVisitor
    def visit_Tuple(node: ast.Tuple, visitor: BaseExpressionVisitor):
        if len(node.elts) != 2:
            raise ValueError("Not 2 elements in tuple")
        
        first, second = node.elts

        if not isinstance(first, ast.Constant) or not isinstance(first.value, str):
            raise ValueError("First element of tuple is not a str")
        
        if not isinstance(second, ast.List) or not all(isinstance(elem, ast.Constant) and isinstance(elem.value, str) for elem in second.elts):
            raise ValueError("Second element is not list of strings")

        return first.value, list(map(lambda elem: elem.value ,second.elts))
    
    while True:
        clss = BaseExpressionVisitor.__subclasses__()
        
        choice = input('\n'.join(f"[{i}] {cls.__name__}" for i, cls in enumerate(clss)) + "\n> ")

        try:
            choice = int(choice)
        except ValueError:
            print("Invalid integer", end="\n\n\n")
            continue

        if choice < 0 or choice >= len(clss):
            print("Integer out of range", end='\n\n\n')
            continue
        
        visitor_cls = clss[choice]

        if issubclass(visitor_cls, (ListOfTupleVisitor, DictOfStrToListOfTupleVisitor)):
            visitor = visitor_cls(visit_Tuple, config=ExpressionVisitorConfig(100))
        else:
            visitor = visitor_cls(config=ExpressionVisitorConfig(100))

        parser = ExpressionParser(visitor, config=ExpressionParserConfig(100, 100))

        while (inp := input("Input: ")) != "exit":
            try:
                print("Result:", x := parser.parse(inp))
            except Exception as e:
                print("Error:", repr(e))

if __name__ == '__main__':
    __main()
