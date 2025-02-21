import ast
from typing import Optional as Opt

class BooleanExpressionVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.parents = []
        super().__init__()

    def _parents_index(self, idx: int) -> Opt[ast.AST]:
        try:
            return self.parents[idx]
        except IndexError:
            return None
        
    # Root (because 'eval' mode)
    def visit_Expression(self, node: ast.Expression):
        return self.visit(node.body)
    
    def visit(self, node: ast.AST):
        self.parents.append(node)
        print(self.parents)
        result = super().visit(node)
        self.parents.pop()
        return result
    
    def visit_BinOp(self, node: ast.BinOp):
        return self.visit(node.left) + self.visit(node.right)
    
    def visit_BoolOp(self, node: ast.BoolOp):
        if not isinstance(node.op, (ast.And, ast.Or)):
            raise SyntaxError("Unsupported boolean operator")
        
        if isinstance(node.op, ast.And):
            return all(self.visit(v) for v in node.values)
        
        return any(self.visit(v) for v in node.values)
    
    # Variable name
    def visit_Name(self, node: ast.Name):
        if not isinstance(self._parents_index(-2), ast.Compare):
            raise SyntaxError("Not part of comparison")

        return "test"

    def visit_Constant(self, node: ast.Constant):
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

code = 'a == "test" or (b == "test" and b == "test")'
tree = ast.parse(code, mode='eval')
visitor = BooleanExpressionVisitor()
result = visitor.visit(tree)
print(result)
