import typing as t
from string.templatelib import Template
from typing import Any, Mapping, Sequence

from discord.app_commands import CheckFailure

from dc_utils.rank import AnyRankT
from structures import BaseStructure, errors

from . import message


class SetupError(RuntimeError):
    """
    Raised when the setup process doesn't fully work.
    Critical, so it stops the process.
    """

    def __init__(self, *args):
        super().__init__(*args)

    def __exception__(self, exc_type, exc_value, traceback):
        exit()


class BaseUserReturnableError(CheckFailure):
    """
    Marks an exception whose string representation can be returned to the user on Discord.
    """

    def __init__(self, *args: t.Any, **msg_kwargs: t.Any) -> None:
        if self.__class__ is BaseUserReturnableError:
            raise RuntimeError(
                f"{self.__class__.__name__} is a base class and must be inherited"
            )

        self.msg_kwargs = msg_kwargs
        super().__init__(*args)


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
        explicit_message_status: message.MessageStatus | None = None,
    ):
        self.header = header
        self.core = core
        self.additional = additional
        self.related_documentation = related_documentation
        self.paragraphs = paragraphs
        self.explicit_message_status = explicit_message_status

        super().__init__(**(msg_kwargs or {}))

    def __str__(self) -> str:
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

        return message.layout(
            header=self.header,
            core=self.core,
            message_status=self.explicit_message_status or message.MessageStatus.ERROR,
            additional=self.additional,
            paragraphs=paragraphs,
        )


class DatabaseError(FeedbackError):
    def __init__(self):
        super().__init__(
            "Database Error",
            t"An error occurred while trying to access or change data in the internal database!",
            additional=t"Try again and if it still doesn't work, try again later.",
        )


class StructureNotFoundViaSyn(FeedbackError):
    def __init__(
        self, syn: str, structure_type: type[BaseStructure], only_name: bool = False
    ) -> None:
        super().__init__(
            f"{structure_type.type_name.title()} Not Found",
            t"The specified {structure_type.type_name} with the name {"" if only_name else "or alias "}{syn:,} could not be found!",
        )


class SynsAlreadyTaken(FeedbackError):
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
            t"The specified {names[many].lower():p} or {aliases[many].lower():p} ({syns:,}) {are[many].lower():p} already taken!",
        )


class InvalidArgument(FeedbackError):
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


class ServerNotConnectedToACommunity(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            "Server Not Connected To A Community",
            t"This server is not connected to a community!",
        )


class ServerAlreadyConnectedToACommunity(FeedbackError):
    def __init__(self, e: errors.ServerAlreadyConnectedToCommunityError) -> None:
        super().__init__(
            "Server Already Connected To A Community",
            t"This server is already connected to a community ({e.community.name:,})!",
        )


class NotEnoughPowerToAffectOtherUsers(FeedbackError):
    def __init__(self, executing_rank: AnyRankT, required_rank: AnyRankT) -> None:
        super().__init__(
            "Not Enough Power To Affect Other Users",
            t"You must at least have the {required_rank.mention()} to execute this command for other users, but you only have the {executing_rank.mention()}!",
        )


class StructureCountLimitReached(FeedbackError):
    def __init__(self, e: errors.StructureCountLimitReachedError) -> None:
        super().__init__(
            f"{e.structure_type.type_name.title()} Count Limit Reached",
            t"The limit of the total amount of {e.structure_type.type_name.lower()}s in this community has been reached, therefore you cannot add any more!",
        )


class SynNotUnique(FeedbackError):
    def __init__(self, e: errors.NotUniqueStringError) -> None:
        super().__init__(
            "Name Or Aliases Not Unique",
            t"The name or alias {e.given:,} has been specified multiple times, but they must be unique!",
        )


class AttributeValueSlotCountOutOfRange(FeedbackError):
    def __init__(self, e: errors.AttributeValueSlotCountOutOfRangeError) -> None:
        super().__init__(
            "Attribute Value Slot Count Out Of Range",
            t"The specified value has not enough or too many slots!",
            additional=t"The value {list(e.value):,} has {len(e.value):,} slots, but the {e.attribute.__class__.type_name.lower()} {e.attribute.name:,} requires between {e.attribute.min_slots:,} and {e.attribute.max_slots:,} slots in a value.",
        )


class CollectionEntryNotFound(FeedbackError):
    def __init__(self, e: errors.CollectionEntryNotFoundError) -> None:
        super().__init__(
            "Collection Entry Not Found",
            t"The specified collection entry {e.real_slot:,} could not be found in the collection of the {e.collection.attribute.__class__.type_name} {e.collection.attribute.name:,}!",
        )


class CollectionEntrySynNotUnique(FeedbackError):
    def __init__(self, e: errors.CollectionEntrySynNotUniqueError) -> None:
        super().__init__(
            "Collection Entry Value Or Alias Not Unique",
            t"The collection entry's value or alias {e.duplicate:,} has been specified multiple times, but they must be unique!",
        )


class EmptyString(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            "Empty String",
            t'You entered an empty or whitespace-only string (`""`), which is not allowed!',
        )


class DoubleBacktick(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            "Double Backtick",
            t"You entered a string that contains a double backtick (`` ` `` `` ` ``), which is not allowed!",
            additional=t"The reason it is not allowed is because otherwise it would be impossible to correctly format Discord messages.",
        )


class AttributeMinSlotsOrMaxSlotsOutOfRange(FeedbackError):
    def __init__(self, e: errors.AttributeMinSlotsOrMaxSlotsOutOfRangeError) -> None:
        super().__init__(
            "Slot Limits Out Of Range",
            t"The min or max slot count specified is invalid!",
            additional=t"`min_slots` must be at least {e.min_min}, while `max_slots` must be at least 1, bigger than `min_slots` and below the community's limit of {e.max_max}.",
            paragraphs=(
                t"The following statement must be valid: `max_slots ≥ 1 and {e.min_min} ≤ min_slots ≤ max_slots ≤ {e.max_max}`.\n"
                t"The values you entered result in this statement: {e.max} ≥ 1 and {e.min_min} ≤ {e.min} ≤ {e.max} ≤ {e.max_max:,}.",
            ),
        )


class TooManyAliases(FeedbackError):
    def __init__(self, e: errors.TooManyAliasesError) -> None:
        super().__init__(
            "Too Many Aliases",
            t"The amount of alises specified is too high. {e.aliases}`!",
        )


class NotPermittedError(FeedbackError):
    def __init__[T: AnyRankT](self, my_rank: T, rank_required: T) -> None:
        self.my_rank = my_rank
        self.rank_required = rank_required
        
        super().__init__(
            "Not Permitted",
            t"You must at least have the {rank_required.mention()}, but your rank is only {my_rank:,}!",
        )


class NotUniqueStructureInMapping(FeedbackError):
    def __init__(
        self,
        structure: BaseStructure,
    ):
        super().__init__(
            f"{type(structure).type_name.title()} Not Unique",
            t"The {type(structure).type_name} {structure:,} has been referenced multiple times as a key in the same mapping, but keys must be unique!",
        )


class DeletionAborted(FeedbackError):
    def __init__(self, structure: BaseStructure) -> None:
        super().__init__(
            "Deletion Aborted",
            t"The deletion of the {type(structure)} {structure:,} was aborted!",
            explicit_message_status=message.MessageStatus.WARNING,
        )
