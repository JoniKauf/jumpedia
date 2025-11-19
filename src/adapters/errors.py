from string.templatelib import Template
from typing import Any, Mapping, Sequence

from discord_.errors import FeedbackError
from structures import BaseStructure, errors
from utils.rank import AnyRankT


class StructureNotFoundViaSynFeedbackError(FeedbackError):
    def __init__(
        self, syn: str, structure_type: type[BaseStructure], only_name: bool
    ) -> None:
        super().__init__(
            f"{structure_type.type_name.title()} Not Found",
            t"The {structure_type.type_name} with the name {"" if only_name else "or alias"}`{syn}` could not be found!",
        )


class SynsAlreadyTakenFeedbackError(FeedbackError):
    def __init__(self, e: errors.SynsAlreadyTakenError) -> None:
        assert e.structures

        syns = tuple(e.structures)

        MAX_EXAMPLES: int = 4

        if len(e.structures) > MAX_EXAMPLES:
            syns = syns[: MAX_EXAMPLES - 1] + ("...",)

        names = ("name", "names")
        aliases = ("alias", "aliases")
        are = ("is", "are")

        many: bool = len(syns) > 1

        super().__init__(
            f"{next(iter(e.structures.values())).__class__.type_name.title()} {names[many].title()} Or {aliases[many].title()} Already Taken",
            t"The specified {names[many].lower():p} or {aliases[many].lower():p} ({'`' + '`, `'.join(syns) + '`':p}) {are[many].lower():p} already taken!",
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


class ServerNotConnectedToACommunityFeedbackError(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            "Server Not Connected To A Community",
            t"This server is not connected to a community!",
        )


class ServerAlreadyConnectedToACommunityFeedbackError(FeedbackError):
    def __init__(self, e: errors.ServerAlreadyConnectedToCommunityError) -> None:
        super().__init__(
            "Server Already Connected To A Community",
            t"This server is already connected to a community (`{e.community.name}`)!",
        )


class NotEnoughPowerToAffectOtherUsersFeedbackError(FeedbackError):
    def __init__(self, executing_rank: AnyRankT, required_rank: AnyRankT) -> None:
        super().__init__(
            "Not Enough Power To Affect Other Users",
            t"You must at least have the {required_rank.mention()} to execute this command for other users, but you only have the {executing_rank.mention()}!",
        )


class StructureCountLimitReachedFeedbackError(FeedbackError):
    def __init__(self, e: errors.StructureCountLimitReachedError) -> None:
        super().__init__(
            f"{e.structure_type.type_name.title()} Count Limit Reached",
            t"The limit of the total amount of {e.structure_type.type_name.lower()}s in this community has been reached, therefore you cannot add any more!"
        )