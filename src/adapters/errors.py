from string.templatelib import Template
from typing import Any, Mapping, Sequence

from utils import text

from discord_.errors import FeedbackError
from structures import BaseStructure, errors


class StructureNotFoundViaSynFeedbackError(FeedbackError):
    def __init__(self, syn: str, structure_type: type[BaseStructure], only_name: bool) -> None:
        super().__init__(
            f"{structure_type.type_name.title()} Not Found",
            t"The {structure_type.type_name} with the name {"" if only_name else "or alias"}`{syn}` could not be found!",
        )

class SynAlreadyTakenFeedbackError(FeedbackError):
    def __init__(self, e: errors.SynsAlreadyTakenError) -> None:
        assert e.structures

        super().__init__(
            "Names Or Aliases Already Taken",
            t"The names or aliases `{'`, `'.join(text.shorten_many(tuple(e.structures)))}` are already taken!"
        )

class InvalidArgumentFeedbackError(FeedbackError):
    def __init__(
        self,
        core: Template,
        *,
        additional: Template | None = None,
        related_documentation: Sequence[tuple[str, str]] = (),
        paragraphs: Sequence[Template] = (),
        msg_kwargs: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(
            "Invalid Argument Error",
            core,
            additional=additional,
            related_documentation=related_documentation,
            paragraphs=paragraphs,
            msg_kwargs=msg_kwargs,
        )
