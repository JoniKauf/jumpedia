import ast
from dataclasses import astuple
import sys
from typing import Any, Callable, Literal, Optional, Self, Sequence, TypeAlias, cast, get_args
from discordtools.errors import InvalidAttributeFeedbackError, ProgrammingError
from trickjump import attributes
from trickjump.trickjump import Trickjump, TrickjumpDataT
from registry.bundles.databases.mariadb import Table
from trickjump.attributes import AttrBase, MultiValueMixin, ATTR_NAMES
from utils import errors

class FilterSyntaxError(Exception):
    pass


class Catalog(list[Trickjump]):

    AttrT: TypeAlias = str
    KeyT: TypeAlias = str | Trickjump
    
    _RAISE_KEY_ERROR = object()

    def __init__(self, data: Optional[Sequence[Trickjump] | Sequence[TrickjumpDataT]] = None, **tj_kwargs: Any):
        if not data:
            super().__init__()
            return
        
        generator = (
            Trickjump(jump, **tj_kwargs) 
            if isinstance(jump, dict) else jump
            for jump in data
        )
        
        super().__init__(generator)
        

    @classmethod
    def get_all_trickjumps(cls, **tj_kwargs: Any) -> Self:
        pass
    

    def contains_name(self, jump_name: str) -> bool:
        jump_name = jump_name.casefold()
        for jump in self:
            if jump.name.value and jump.name.value.casefold() == jump_name:
                return True
        return False
    
    
    @staticmethod
    def jump_name_eq(jump: Trickjump, jump_name: str) -> bool:
        return bool(jump.name.value) and jump.name.value.casefold() == jump_name


    def get_by_name(self, jump_name: str, default: Optional[Trickjump] = None) -> Optional[Trickjump]:
        jump_name = jump_name.casefold()

        for jump in self:
            if Catalog.jump_name_eq(jump, jump_name):
                return jump
        return default
    

    def name_index(self, jump_name: str, default: Optional[int] = None) -> Optional[int]:
        jump_name = jump_name.casefold()
        for index, jump in enumerate(self):
            if Catalog.jump_name_eq(jump, jump_name): 
                return index
        return default
    

    def pop_by_name(self, jump_name: str, default: Optional[Trickjump]) -> Optional[Trickjump]:
        jump_name = jump_name.casefold()
        for index, jump in enumerate(self):
            if Catalog.jump_name_eq(jump, jump_name):
                return self.pop(index)
        return default
    

    def filter(self, expression: Optional[str] = None):
        """Filters the base to only include matching jumps according to a custom syntax."""
        
        if not expression or not self:
            return
        
        def raise_syn_err(feedback: str, docs: Optional[Sequence[str]] = None):
            raise FeedbackError(
                error="Filter Syntax",
                details=feedback,
                docs=docs
            )
        
        # TODO: Improve performance -> Calculations besides getting jump info are
        # always the same, therefore repeated without reasoning for every jump
        class TrickJumpNodeVisitor(ast.NodeVisitor):
            def __init__(self, trickjump: Trickjump):
                # last element will always be the currently visited function node
                self.parents: list[ast.AST] = []
                self.trickjump = trickjump

            def visit(self, node: ast.AST):
                self.parents.append(node)
                result = super().visit(node)
                self.parents.pop()
                return result

            # Replaces attribute name with value/s
            def visit_Name(self, node: ast.Name):
                attr = attributes.syn_to_name(node.id)

                if attr is None:
                    raise_syn_err(f"The attribute `{node.id}` doesn't exist")
                
                if len(self.parents) < 2 or not isinstance(self.parents[-2], (ast.Compare, ast.List)):
                    raise_syn_err(f"The attribute `{attr}` is not part of a comparison or list")

                val = getattr(self.trickjump, attr, '')

                if isinstance(val, tuple):
                    return tuple(e.casefold() for e in val)
                else:
                    return val.casefold()
            
            # String literals
            def visit_Str(self, node: ast.Constant):
                val: str = node.value.casefold()

                if len(self.parents) < 2 or not isinstance(self.parents[-2], (ast.Compare, ast.List)):
                    raise_syn_err(f"The value `{val}` is not part of a comparison or list")
                
                return val

            def visit_List(self, node: ast.List):
                if len(self.parents) < 2 or not isinstance(self.parents[-2], ast.Compare):
                    raise_syn_err(f"The list `{ast.unparse(node)}` is not part of a comparison")
                
                result = []
                
                for elem in node.elts:
                    if not isinstance(elem, ast.Constant):
                        raise_syn_err(f"A list must only contain values, not `{ast.unparse(elem)}`")
                    
                    result.append(self.visit(elem))

                return result
            
            # Bool operators
            def visit_BoolOp(self, node: ast.BoolOp):
                generator = (self.visit(value) for value in node.values)

                if isinstance(node.op, ast.Or):
                    return any(generator)
                elif isinstance(node.op, ast.And):
                    return all(generator)
                else:
                    raise errors.ProgrammingError(f"The boolean operator '{node.op}' is invalid")
            
            def visit_Compare(self, node: ast.Compare):
                left = self.visit(node.left)
                operator = node.ops[0]
                right = self.visit(node.comparators[0])

                left = {left} if isinstance(left, str) else set(left)
                right = {right} if isinstance(right, str) else set(right)

                result = False

                if isinstance(operator, (ast.In, ast.NotIn)):
                    result = any(e in f for e in left for f in right)
                elif isinstance(operator, (ast.Is, ast.IsNot)):
                    result = any(e == f for e in left for f in right)
                else:
                    raise_syn_err("A value can only be compared to an attribute with 'in' or 'is'")
                
                return result if isinstance(operator, (ast.Is, ast.In)) else not result

            def generic_visit(self, node: ast.AST):
                raise_syn_err("Invalid type of argument")


        # Massive help from ChatGPT to make this possible
        def syntax_parser(expression: str, tj: Trickjump) -> bool:
            # Parse the expression into an AST
            try:
                parsed_ast = ast.parse(expression, mode='eval')
            except Exception:
                raise_syn_err("The syntax input is malformed")
            
            # Visit the AST nodes
            visitor = TrickJumpNodeVisitor(tj)
            result: bool = visitor.visit(parsed_ast.body)

            return result
        
        for i in range(len(self) -1, -1, -1):
            if not syntax_parser(expression, self[i]):
                self.pop(i)

    
    @staticmethod
    def _resolve_bad_attrs(bad_attrs: Optional[Sequence[str]], base: Sequence[type[AttrBase]] = ()) -> list[type[AttrBase]]:
        if not bad_attrs:
            return []
        
        result: list[type[AttrBase]] = list(base)

        for bad_attr in bad_attrs:
            try:
                attr = attributes.syn_to_cls(bad_attr)
            except KeyError:
                raise InvalidAttributeFeedbackError(bad_attr)
            
            result.append(attr)

        # keep order while removing duplicates
        return list(dict.fromkeys(result))
    


    def sort(self, bad_attrs: Optional[Sequence[str]] = None) -> None:
        """
        Sorts the base defined by the attributes specified with priority.
        """
        
        # No sorting required for 0 or 1 elems or no sorting requirements
        if not bad_attrs or len(self) <= 1:
            return
        
        SIGN_SYMBOL = "-"
        attrs_sign: dict[type[AttrBase], Literal[1, -1]] = {}

        for attr in bad_attrs:
            try:
                attr_cls = attributes.syn_to_cls(attr.removeprefix(SIGN_SYMBOL).casefold())
            except KeyError:
                raise InvalidAttributeFeedbackError(attr)
            
            attrs_sign[attr_cls] = -1 if attr.startswith(SIGN_SYMBOL) else +1

        
        def get_sort_val(jump: Trickjump) -> tuple:
            return tuple(jump.get(attr_cls).sort_key(sign) for attr_cls, sign in attrs_sign.items())
        
        super().sort(key=get_sort_val)


    def get_yield(self, bad_attrs: Optional[Sequence[AttrT]], replace: Callable[[Any], Any]) -> list[tuple[Any, ...]]:
        attrs = Catalog._resolve_bad_attrs(bad_attrs, [attributes.Name])

        yield_ = []
        
        for tj in self:
            values: tuple[AttrBase, ...] = astuple(tj)
            
            yield_.append(
                tuple(replace(v.value) for v in values)
            )
        
        return yield_