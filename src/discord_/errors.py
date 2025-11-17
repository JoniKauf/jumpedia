import enum
import typing as t
from string.templatelib import Template

from discord.app_commands.errors import CheckFailure


class BaseUserReturnableError(RuntimeError, CheckFailure):
    """
    Marks an exception whose string representation can be returned to the user on Discord.
    """

    def __init__(self, *args: t.Any, **msg_kwargs: t.Any) -> None:
        if self.__class__ == BaseUserReturnableError:
            raise RuntimeError(
                f"{self.__class__.__name__} is a base class and must be inherited"
            )

        self.msg_kwargs = msg_kwargs
        super().__init__(*args)


class SetupError(RuntimeError):
    """
    Raised when the setup process doesn't fully work.
    Critical, so it stops the process.
    """

    def __init__(self, *args):
        super().__init__(*args)

    def __exception__(self, exc_type, exc_value, traceback):
        exit()


class FeedbackError(BaseUserReturnableError):
    """Its string representation shows a customizable, user-friendly error message."""

    def __init__(
        self,
        header: str,
        core: Template,
        *,
        additional: Template | None = None,
        related_documentation: t.Sequence[tuple[str, str]] = (),
        paragraphs: t.Sequence[Template] = (),
        msg_kwargs: t.Mapping[str, t.Any] | None = None,
    ):
        self.header = header
        self.core = core
        self.additional = additional
        self.related_documentation = related_documentation
        self.paragraphs = paragraphs

        super().__init__(**(msg_kwargs or {}))

    def __str__(self) -> str:
        from .utils_ import messaging

        paragraphs: list[Template] = list(self.paragraphs)

        if self.related_documentation:
            paragraphs.append(
                t"### Related Documentation\n"
                + Template(
                    "\n".join(
                        f"[{name}]({link})" for name, link in self.related_documentation
                    )
                )
            )

        return messaging.layout(
            header=self.header,
            core=self.core,
            message_status=messaging.MessageStatus.ERROR,
            additional=self.additional,
            paragraphs=paragraphs,
        )
