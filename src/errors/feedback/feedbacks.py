import textwrap
from typing import TYPE_CHECKING, Any
from errors.feedback import FeedbackError
from discordtools import messaging as msg
from structures import BaseStructure

if TYPE_CHECKING:
    from structures.community import Community
    
def server_already_connected_to_community(current_community: 'Community', new_community: 'Community | None' = None) -> FeedbackError:
    if new_community is not None and new_community == current_community:
        return FeedbackError(
            "Server Already Connected To Specified Community",
            f"This server is already connected to the specified community ({msg.code(current_community.real_name)})!"
        )
    
    import cogs.jumpedia

    connect_cmd = cogs.jumpedia.JumpediaCog.connect_community.qualified_name
    disconnect_cmd = cogs.jumpedia.JumpediaCog.disconnect_community.qualified_name

    return FeedbackError(
        "Server Already Connected To A Community",
        f"This server is already connected to a different community called {msg.code(current_community.real_name)}!",
        additional="A server can only be connected to one community at a time.",
        paragraphs=[
            f"If you want to change the community for this server, see the commands "
            f"{msg.code(connect_cmd)} and {msg.code(disconnect_cmd)}."
        ]
    ) 

def name_ends_in_structure_name(name: str, structure: type[BaseStructure]) -> FeedbackError:
    return FeedbackError(
        f"Name Ends In {structure.get_structure_name(True)}",
        f"The name of the specified {structure.get_structure_name()} ends in {msg.code(name)}!",
        additional="Please leave that part out of the name, as it is redundant and it makes feedback messages more confusing to understand."
    )


def invalid_attribute_value_mapping(additional_what_is_wrong_exactly: str) -> FeedbackError:
    return FeedbackError(
        "Invalid Attribute Value Mapping",
        "The specified attribute value mapping is not valid.",
        additional=additional_what_is_wrong_exactly,
        paragraphs=[
            "A valid attribute value mapping must be a JSON string representing an object "
            "that maps at least all required (min_slots > 0) task attributes to a single item or "
            "list of values.",

            "For example, assume a task represents a chore somebody has to do at home in a "
            "hypothetical community and assume there are two required task attributes called "
            f"{msg.code("amount")} and {msg.code("more_info")}.",

            "Now an attribute value mapping would look something like this:\n"
            f"{msg.code_big(textwrap.dedent("""
                {
                    "amount": 2,
                    "more_info": [
                        "TODO before mom comes home!!",
                        "Do this chore first!"         
                    ]                  
                }
            """))}",

            f"This would mean that the new task now has the value {msg.code(str(2))} "
            f"for the task attribute {msg.code("amount")} and the two specified texts "
            f"for the task attribute {msg.code("more_info")}."
        ]
    )

def temp(*args: Any, **kwargs: Any) -> FeedbackError:
    return FeedbackError(
        "Temporary Error!",
        "Data:" + 
        ("Args:" + msg.code_big('\n'.join(args))) if args else '' +
        ("KWArgs:" + msg.code_big('\n'.join(f"{k}: {v}" for k, v in kwargs.items())) if kwargs else '')
    )