import math
from typing import Any, Callable, Hashable, Iterable, Optional as Opt

type TreeT[T: Hashable] = dict[T, TreeT[T]]

class _TreeNode[T: Hashable]:
    def __init__(self, value: T, parent: Opt['_TreeNode[T]'], children: list['_TreeNode[T]']) -> None:
        self.value = value
        self.parent = parent
        self.children = children
    
    def __eq__(self, value: object) -> bool:
        return isinstance(value, self.__class__) and self.__dict__ == value.__dict__
    
    def __repr__(self) -> str:
        return f'{type(self).__name__}({",".join(
            f"{k!r}={v!r}" 
            for k, v in self.__dict__.items() 
            if not k.startswith("__")
        )})'
    
    def __str__(self) -> str:
        return str(self.value)
    
    def value_equals(self, other: '_TreeNode[T]') -> bool:
        return self.value == other.value


class Tree[T: Hashable]:
    def __init__(self, tree: TreeT[T], normalize: Callable[[T], T], max_depth: int, max_nodes: int, max_children: int) -> None:
        self._normalize = normalize
        self._node_lookup: dict[T, _TreeNode[T]] = {}
        self._roots: list[_TreeNode[T]] = []

        self._max_depth = max(1, max_depth)
        self._max_nodes = max(1, max_nodes)
        self._max_children = max(1, max_children)

        self._build_tree(None, tree, 1)

    def __str__(self) -> str:
        return self._str(self._roots, "")

    def _str(self, nodes: list[_TreeNode[T]], prefix: str) -> str:
        result = []
        for i, node in enumerate(nodes):
            is_last_child = (i == len(nodes) - 1)
            connector = "└── " if is_last_child else "├── "
            
            result.append(f"{prefix}{connector}{node.value}")
            
            new_prefix = prefix + ("    " if is_last_child else "│   ")
            subtree = self._str(node.children, new_prefix)

            if subtree:
                result.append(subtree)

        return "\n".join(result)

    def _build_tree(self, parent: Opt['_TreeNode[T]'], children_tree: TreeT[T], depth: int) -> list[_TreeNode[T]]:
        if depth > self._max_depth:
            raise MaxDepthExceededError()
        
        children: list[_TreeNode[T]] = []

        for child_value, child_children_tree in children_tree.items():
            child_value_norm = self._normalize(child_value)

            if child_value_norm in self._node_lookup:
                raise DuplicateValueError(child_value_norm)

            self._node_lookup[child_value_norm] = child

            child = _TreeNode(
                child_value_norm,
                parent,
                []
            )

            if len(self._node_lookup) > self._max_nodes:
                raise MaxNodesExceededError()
            
            child.children = self._build_tree(
                child,
                child_children_tree,
                depth + 1
            ) 

            children.append(child)
        
        if len(children) > self._max_children:
            raise MaxChildrenExceededError(parent)
        
        if parent is None:
            self._roots.extend(children)

        return children
    

class TreeError(ValueError):
    pass

class MaxDepthExceededError(TreeError):
    pass

class MaxNodesExceededError(TreeError):
    pass

class DuplicateValueError(TreeError):
    def __init__(self, duplicate: Any, *args: object) -> None:
        self.duplicate = duplicate

        super().__init__(*args)

class MaxChildrenExceededError(TreeError):
    def __init__(self, node: _TreeNode | None, *args: object) -> None:
        self.node = node
        super().__init__(*args)