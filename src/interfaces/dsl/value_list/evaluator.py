from interfaces.dsl.shared.transformer import StringNode, get_string_from_stringy_node
from interfaces.dsl.value_list.transformer import ValueListNode


class ValueListEvaluator:
    def evaluate(self, node: ValueListNode) -> list[str]:
        return [get_string_from_stringy_node(elem) for elem in node.elements]
