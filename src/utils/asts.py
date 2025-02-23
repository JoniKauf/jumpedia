import ast
from typing import Optional as Opt
from trickjump import attributes as attrs, catalog as cat, trickjump as tj

class BooleanExpressionVisitor(ast.NodeVisitor):
    def __init__(self, trickjumps: cat.Catalog) -> None:
        self.parents = []
        self.trickjumps = trickjumps
        super().__init__()

    def _parents_index(self, idx: int) -> Opt[ast.AST]:
        try:
            return self.parents[idx]
        except IndexError:
            return None
    
    def _valid_2_sided(self, node: ast.AST, is_left: bool):
        parent: ast.AST = self.parents[-2]

        if not isinstance(parent, ast.Compare):
            raise SyntaxError("Not part of comparison")
        
        if is_left and parent.left != node or not is_left and parent.left == node:
            raise SyntaxError("Wrong side of comparison")
    
    def visit(self, node: ast.AST):
        self.parents.append(node)
        result = super().visit(node)
        self.parents.pop()
        return result
    
    # Root (because 'eval' mode)
    def visit_Expression(self, node: ast.Expression):
        if self.parents != [node]:
            raise SyntaxError("Expression at non-root")
        
        filtered = cat.Catalog()

        for tj in self.trickjumps:
            self.tj = tj

            if self.visit(node.body):
                filtered.append(self.tj)

        return filtered
                
    def visit_BoolOp(self, node: ast.BoolOp): 
        if isinstance(node.op, ast.And):
            return all(self.visit(v) for v in node.values)
        
        if isinstance(node.op, ast.Or):
            return any(self.visit(v) for v in node.values)
        
        raise SyntaxError("Unsupported boolean operator")
    
    def visit_BinOp(self, node: ast.BinOp):
        if not isinstance(node.left, ast.Name):
            raise SyntaxError("Left part is not variable")
        if not isinstance(node.right, ast.Constant):
            raise SyntaxError("Right part is not constant")
        if not isinstance(node.right.value, str):
            raise SyntaxError("Right part is not string")
        
        return self.visit(node.left) == self.visit(node.right)
    
    # Variable name
    def visit_Name(self, node: ast.Name):
        try:
            attr = attrs.syn_to_name(node.id)
        except KeyError:
            raise SyntaxError(f"Invalid attr '{node.id}'")
        
        return self.tj.get_attr(attr).value   

    def visit_Constant(self, node: ast.Constant):
        if not isinstance(node.value, str):
            raise SyntaxError("must be string")
        if not isinstance(self._parents_index(-2), ast.Compare):
            raise SyntaxError("Not part of comparison")
        
        return node.value
    
    def visit_Compare(self, node: ast.Compare):
        if len(node.comparators) != 1 or len(node.ops) != 1:
            raise SyntaxError("Not exactly 1 comparator or operator")
        
        if isinstance(node.ops[0], ast.Eq):
            return self.visit(node.left) == self.visit(node.comparators[0])
        
        raise SyntaxError("Not a valid comparison")
    
    def generic_visit(self, node: ast.AST):
        raise SyntaxError("Generic Visit")

code = """name == "Among Us" or name == 'a'"""
tree = ast.parse(code, mode='eval')
visitor = BooleanExpressionVisitor(tj.Trickjump.get_all())
import time

start = time.time()
result = visitor.visit(tree)
print(time.time() - start)
print(result)
