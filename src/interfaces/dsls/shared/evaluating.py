from interfaces.dsls.shared.parsing import StringNode, TextNodeT


def get_string_from_text_node(node: TextNodeT) -> str:
    if isinstance(node, StringNode):
        return node.value

    return node.name
