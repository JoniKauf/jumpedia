from typing import Callable, Hashable, Iterable, Optional as Opt, cast

type TreeT[T: Hashable] = dict[T, TreeT[T]]

class _TreeNode[T: Hashable]:
    def __init__(self, value: T, children: Iterable['_TreeNode[T]']) -> None:
        self.nodes = set(children)
        self._value = value

    def __hash__(self) -> int:
        return hash(self._value)
    
    def __eq__(self, value: object) -> bool:
        if not isinstance(value, _TreeNode):
            return False
        return self._value == value._value


class Tree[T: Hashable]:
    MAX_DEPTH = 64

    def __init__(self, tree: TreeT[T], normalize: Callable[[T], T]) -> None:
        self._normalize = normalize
        self._unnormalize: dict[T, T] = {}
        self._nodes: set[_TreeNode[T]] = self._build_tree(type, tree, 0)

    def __str__(self) -> str:
        return self._str(self._nodes, 0)

    def _str(self, nodes: set[_TreeNode[T]], depth: int) -> str:
        result = []
        
        for i, node in enumerate(nodes):
            prefix = '└' if i == len(nodes) - 1 else '├'

            result.append(f"{prefix} {' ' * (depth * 2)}{self._unnormalize[node._value]}")
            subtree = self._str(node.nodes, depth + 1)

            if subtree:
                result.append(subtree)

        return "\n".join(result)

    def _build_tree(self, node_vs: tuple[T, T] | type, child_nodes: TreeT[T], depth: int) -> set[_TreeNode[T]]:
        if not isinstance(node_vs, type):
            node_v, node_v_norm = node_vs
            
            if depth > self.__class__.MAX_DEPTH:
                raise ValueError("recursion limit")
            
            if node_v_norm in self._unnormalize:
                raise ValueError("duplicate")
            
            self._unnormalize[node_v_norm] = node_v

        result: set[_TreeNode[T]] = set()

        for child_node_v, grandchild_nodes in child_nodes.items():
            child_node_v_norm = self._normalize(child_node_v)

            tree_node = _TreeNode(
                child_node_v_norm, 
                self._build_tree(
                    (child_node_v, child_node_v_norm), 
                    grandchild_nodes, 
                    depth + 1
            ))
            
            result.add(tree_node)

        return result  