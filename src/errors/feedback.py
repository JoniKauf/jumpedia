from errors import BaseFeedbackError
import structures as structs
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
            body=f"The {structs_type_lower} with the specified name {msg.shorten_and_embed(name)} could not be found!"
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
                f"The format {msg.shorten_and_embed(format)} specified for the user is invalid. "
                "Either mention a user with `@` or copy and paste their id."
            )
        )