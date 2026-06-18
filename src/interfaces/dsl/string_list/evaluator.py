from interfaces.dsl.shared.transformer import StringNode
from interfaces.dsl.string_list.transformer import ListNode


class Evaluator:
    def evaluate(self, node: ListNode) -> list[str]:
        return [
            elem.value if isinstance(elem, StringNode) else elem.name
            for elem in node.elements
        ]
