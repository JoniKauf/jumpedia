import ast
from typing import Iterable, Optional as Opt
from trickjump import attribute as attrs
from trickjump.catalog import List
from trickjump.trickjump import Trickjump
from utils import devtools as dev

class TrickjumpFilterNodeVisitor(ast.NodeVisitor):
    def __init__(self, trickjumps: Iterable[Trickjump]) -> None:
        self.parents = []
        self.filtered: set[Trickjump] = set(trickjumps)

        super().__init__()

    def _parents_index(self, idx: int) -> Opt[ast.AST]:
        try:
            return self.parents[idx]
        except IndexError:
            return None

    def visit(self, node: ast.AST):
        self.parents.append(node)

        try:
            result = super().visit(node)
        except SyntaxError as e:
            raise SyntaxError(e.msg + " | " + str(self.parents))
        
        self.parents.pop()
        return result
    
    # Root (because 'eval' mode)
    def visit_Expression(self, node: ast.Expression):
        if self.parents != [node]:
            raise SyntaxError("Expression at non-root")

        self.filtered = self.visit(node.body)

        return self.filtered
                
    def visit_BoolOp(self, node: ast.BoolOp): 
        if not isinstance(self._parents_index(-2), ast.Expression):
            raise SyntaxError("Expression expected")

        if isinstance(node.op, ast.And):
            for n in node.values:
                self.filtered = self.visit(n)

        elif isinstance(node.op, ast.Or):
            result: set[Trickjump] = set()

            for n in node.values:
                result |= self.visit(n)

            self.filtered = result
        else:
            raise SyntaxError("Unsupported boolean operator")
    
        return self.filtered
    
    def visit_BinOp(self, node: ast.BinOp):
        if not isinstance(self._parents_index(-2), (ast.BoolOp, ast.Expression)):
            raise SyntaxError("Not child of boolOp or Expression")
        if not isinstance(node.left, ast.Name):
            raise SyntaxError("Left part is not variable")
        if not isinstance(node.right, ast.Constant):
            raise SyntaxError("Right part is not constant")
        if not isinstance(node.right.value, str):
            raise SyntaxError("Right part is not string")
        if not isinstance(node.op, ast.Div):
            raise SyntaxError("Not a div")
        
        attr: str = self.visit(node.left)
        literal: str = self.visit(node.right)

        #TODO
    
    def visit_Compare(self, node: ast.Compare):
        if not isinstance(self._parents_index(-2), (ast.BoolOp, ast.Expression)):
            raise SyntaxError("Not child of boolOp or Expression")
        
        if not isinstance(node.left, ast.Name):
            raise SyntaxError("Left part is not variable")
        
        if len(node.comparators) != 1 or len(node.ops) != 1:
            raise SyntaxError("Not exactly 1 comparator or operator")
        
        if not isinstance(node.comparators[0], ast.Constant):
            raise SyntaxError("Right part is not constant")
        
        if not isinstance(node.comparators[0].value, str):
            raise SyntaxError("Right part is not string")
        
        if not isinstance(node.ops[0], ast.Eq):
            raise SyntaxError("Not a valid comparison")
        
        attr: attrs.AttrNormalT = self.visit(node.left)
        literal: str = self.visit(node.comparators[0])
        
        result: set[Trickjump] = set()

        if Trickjump.field_value_type_info()[attr.value_cls]:
            for tj in self.filtered:
                attr_obj = tj.get_attr(attr.value_cls.NAME)

                if literal == str(attr_obj):
                    result.add(tj)
        else:
            for tj in self.filtered:
                for attr_obj in attr:
                    if literal == str(attr_obj):
                        result.add(tj)
        
        return result
        
    
    # Variable name
    def visit_Name(self, node: ast.Name):
        try:
            attr = attrs.syn_to_cls(node.id)
        except KeyError:
            raise SyntaxError(f"Invalid attr '{node.id}'")
        
        return attr

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, str):
            raise SyntaxError("must be string")
        if not isinstance(self._parents_index(-2), (ast.Compare, ast.BinOp)):
            raise SyntaxError("Not part of comparison")
        
        return node.value
    
    def generic_visit(self, node: ast.AST):
        raise SyntaxError("Generic Visit")

code = """name == 'Vault' or name == 'Metro Impossible'"""
tree = ast.parse(code, mode='eval')

with dev.timed("Get all jumps"):
    jumps = Trickjump.get_all()

with dev.timed("Create visitor"):
    visitor = TrickjumpFilterNodeVisitor(jumps)

with dev.timed("Determine result"):
    result = visitor.visit(tree)

print(len(result))
