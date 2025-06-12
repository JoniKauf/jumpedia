from typing import Any, Sequence
from errors import BaseFeedbackError
import structures as structs
from structures.attributes import AttributeValueType
from utils import text
from discordtools import messaging as msg

class __Template(BaseFeedbackError):
    def __init__(
        self, 
    ) -> None:
        pass

class StructuresNotFound(BaseFeedbackError):
    def __init__(
        self, 
        structures: structs.StructuresTypeT,
        name: str | None = None,
    ) -> None:
        structs_type_lower = structs.human_join_structures_type(structures, str.lower)
        
        super().__init__(
            header=f"{structs.human_join_structures_type(structures, str.title)} Not Found",
            body=f"The {structs_type_lower} with the specified name {msg.shorten_and_code(name)} could not be found!"
            if name else
            f"The specified {structs_type_lower} could not be found!"
        )

class InvalidUserFormat(BaseFeedbackError):
    def __init__(
        self, 
        format: str
    ) -> None:
        super().__init__(
            header=f"Invalid User Format",
            body=(
                f"The format {msg.shorten_and_code(format)} for specifying a user is invalid! "
                "Either mention a user with `@` or enter their id."
            )
        )


class InvalidValue(BaseFeedbackError):
    def __init__(
        self, 
        value: str,
        value_is_invalid_because: str,
        additional: str = ''
    ) -> None:
        super().__init__(
            header=f"Invalid Value",
            body=(
                f"The specified value {msg.shorten_and_code(value)} is not valid "
                f"because {value_is_invalid_because}!" +
                ("" if not additional else f'\n{additional}')
            )
        )


class InvalidValueForAttributeValueType(BaseFeedbackError):
    def __init__(
        self, 
        value: str,
        expected_attribute_value_type: AttributeValueType
    ) -> None:
        super().__init__(
            header=f"Invalid Value",
            body=(
                f"The specified value {msg.shorten_and_code(value)} is not valid "
                f"because it should represent a value of type {msg.code(expected_attribute_value_type.name)}!"
            )
        )


class MaxDepthExceeded(BaseFeedbackError):
    def __init__(
        self,
        max_depth: int,
        for_what: str
    ) -> None:
        super().__init__(
            header=f"Max Depth Exceeded",
            body=(
                f"You have exceeded the max depth of {max_depth} for the specified {for_what}!"
            )
        )


class TemporaryFeedbackError(BaseFeedbackError):
    def __init__(
        self,
        *args, 
    ) -> None:
        super().__init__(
            header="Temporary Feedback Error",
            body="Temporary Error!\n" + '\n'.join(f"- {msg.code(str(arg))}" for arg in args)
        )