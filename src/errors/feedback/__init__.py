from typing import Any, Mapping, Sequence
from discordtools import messaging
from errors import BaseUserReturnableError


class FeedbackError(BaseUserReturnableError):
    """Its string representation shows a customizable, user-friendly error message."""

    def __init__(self, header: str, core: str, *, additional: str | None = None, related_documentation: Sequence[tuple[str, str]] = (), paragraphs: Sequence[str] = (), msg_kwargs: Mapping[str, Any] | None = None):
        self.header = header
        self.core = core
        self.additional = additional
        self.related_documentation = related_documentation
        self.paragraphs = paragraphs

        super().__init__(**(msg_kwargs or {}))
    

    def __str__(self) -> str:
        paragraphs: list[str] = list(self.paragraphs)

        if self.related_documentation:
            paragraphs.append(
                "### Related Documentation\n" 
                + 
                '\n'.join(
                    f"[{name}]({link})" 
                    for name, link in 
                    self.related_documentation
                )
            )

        return messaging.layout(
            header=self.header,
            core=self.core,
            message_status=messaging.MessageStatus.FAILED,
            paragraphs=paragraphs
        )