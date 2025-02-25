import ast
from typing import Iterable, Optional as Opt
from trickjump import attributes as attrs
from trickjump.catalog import Catalog
from trickjump.trickjump import Trickjump
from utils import devtools as dev

class BooleanExpressionVisitor(ast.NodeVisitor):
    def __init__(self, trickjumps: Iterable[Trickjump]) -> None:
        self.parents = []
        self.order: dict[Trickjump, int] = {tj: i for i, tj in enumerate(trickjumps)}
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

        result: set[Trickjump] = self.visit(node.body)

        return Catalog(
            tj for tj in sorted(result, key=lambda t: self.order[t])
        )
                
    def visit_BoolOp(self, node: ast.BoolOp): 
        if not isinstance(self._parents_index(-2), ast.Expression):
            raise SyntaxError("Expression expected")

        if isinstance(node.op, ast.And):
            for n in node.values:
                self.filtered = self.visit(n)
        elif isinstance(node.op, ast.Or):
            for n in node.values:
                self.filtered |= self.visit(n)
        else:
            raise SyntaxError("Unsupported boolean operator")
    
        return self.filtered
    
    def visit_BinOp(self, node: ast.BinOp):
        if isinstance(self._parents_index(-2), (ast.BoolOp, ast.Expression)):
            raise SyntaxError("Not child of boolOp or Expression")
        if not isinstance(node.left, ast.Name):
            raise SyntaxError("Left part is not variable")
        if not isinstance(node.right, ast.Constant):
            raise SyntaxError("Right part is not constant")
        if not isinstance(node.right.value, str):
            raise SyntaxError("Right part is not string")
        
        if not isinstance(node, ast.Div):
            raise SyntaxError("Not a div")
        
        attr: str = self.visit(node.left)
        literal: str = self.visit(node.right)

        self.filtered = {
            tj for tj in self.filtered 
            if str(tj.get_attr(attr)) in literal
        }
        for tj in self.filtered:
            if 
        if not  in :
            self.filtered.remove(tj)

        return self.filtered
    
    def visit_Compare(self, node: ast.Compare):
        if isinstance(self._parents_index(-2), (ast.BoolOp, ast.Expression)):
            raise SyntaxError("Not child of boolOp or Expression")
        
        if not isinstance(node.left, ast.Name):
            raise SyntaxError("Left part is not variable")
        
        if len(node.comparators) != 1 or len(node.ops) != 1:
            raise SyntaxError("Not exactly 1 comparator or operator")
        
        if not isinstance(node.comparators[0], ast.Constant):
            raise SyntaxError("Right part is not constant")
        if not isinstance(node.comparators[0].value, str):
            raise SyntaxError("Right part is not string")
        
        if isinstance(node.ops[0], ast.Eq):
            return self.visit(node.left) == self.visit(node.comparators[0])
        
        raise SyntaxError("Not a valid comparison")
    
    # Variable name
    def visit_Name(self, node: ast.Name):
        try:
            attr = attrs.syn_to_name(node.id)
        except KeyError:
            raise SyntaxError(f"Invalid attr '{node.id}'")
        
        return attr

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, str):
            raise SyntaxError("must be string")
        if not isinstance(self._parents_index(-2), ast.Compare):
            raise SyntaxError("Not part of comparison")
        
        return node.value
    
    def generic_visit(self, node: ast.AST):
        raise SyntaxError("Generic Visit")

code = """name == "Among Us" or name == 'a'"""
tree = ast.parse(code, mode='eval')

with dev.timed("Get all jumps"):
    jumps = tj.Trickjump.get_all()

with dev.timed("Create visitor"):
    visitor = BooleanExpressionVisitor(jumps)

with dev.timed("Determine result"):
    result = visitor.visit(tree)

print(len(result), [tj.name for tj in result])
