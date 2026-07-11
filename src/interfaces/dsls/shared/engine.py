from interfaces.dsls.shared.parse import StringNode, TextNodeT


class BaseEngine:
    def get_string_from_text_node(self, node: TextNodeT) -> str:
        if isinstance(node, StringNode):
            return node.value

        return node.name
