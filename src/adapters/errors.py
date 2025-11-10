from string.templatelib import Template
from typing import Any, Mapping, Sequence

from ..discord_.errors import FeedbackError
from ..structures import BaseStructure, errors


class StructureNotFoundViaSynFeedbackError(FeedbackError):
    def __init__(self, syn: str, structure_type: type[BaseStructure]) -> None:
        super().__init__(
            f"{structure_type.type_name.title()} Not Found",
            t"The {structure_type.type_name} with the name or alias `{syn}` could not be found!",
        )

class SynAlreadyTakenFeedbackError(FeedbackError):
    def __init__(self, e: errors.SynsAlreadyTakenError) -> None:
        assert isinstance(e.structure, BaseStructure)

        super().__init__(
            "Name Or Alias Already Taken",
            t"The name or alias `{e.syn}` is already taken by another {e.structure.__class__.type_name:p}!"
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
