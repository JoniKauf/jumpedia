from typing import Callable, Hashable, Iterable, Optional as Opt

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
    MAX_DEPTH = 64

    def __init__(self, tree: TreeT[T], normalize: Callable[[T], T]) -> None:
        self._normalize = normalize
        self._node_lookup: dict[T, _TreeNode[T]] = {}
        self._roots: list[_TreeNode[T]] = []

        self._build_tree(None, tree, 0)

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
        if depth > self.__class__.MAX_DEPTH:
            raise ValueError("recursion limit")
        
        children: list[_TreeNode[T]] = []

        for child_value, child_children_tree in children_tree.items():
            child_value_norm = self._normalize(child_value)

            if child_value_norm in self._node_lookup:
                raise ValueError("Duplicate normalized value")

            child = _TreeNode(
                child_value,
                parent,
                []
            )

            self._node_lookup[child_value_norm] = child

            child.children = self._build_tree(
                child,
                child_children_tree,
                depth + 1
            ) 

            children.append(child)

        if parent is None:
            self._roots.extend(children)

        return children