from interfaces.dsl.shared.transformer import StringNode, get_string_from_stringy_node
from interfaces.dsl.value_to_value_list_mapping.transformer import (
    ValueListNode,
    ValueToValueListMappingNode,
)


class ValueToValueListMappingEvaluator:
    def evaluate(self, node: ValueToValueListMappingNode) -> dict[str, list[str]]:
        return {
            get_string_from_stringy_node(item.key): [
                get_string_from_stringy_node(elem) for elem in item.value.elements
            ]
            for item in node.items
        }
