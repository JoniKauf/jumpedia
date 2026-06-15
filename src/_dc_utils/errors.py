import typing as t
from collections import namedtuple
from operator import add
from string.templatelib import Template
from typing import Any, Mapping, Sequence

from discord.app_commands import CheckFailure
from structures import BaseStructure, BaseStructureWithAliases, errors
from structures.task import Task
from structures.user import CommunityUser

from _dc_utils import layouts
from domain.enum.rank import AnyRankT
from utils import gist, text

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
    def __init__(self, syn: str, structure_type: type[BaseStructure]) -> None:
        super().__init__(
            f"{structure_type.type_name.title()} Not Found",
            t"The specified {structure_type.type_name} with the name {"or alias " if issubclass(structure_type, BaseStructureWithAliases) else ""}{syn:,} could not be found!",
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
            t"You must at least have the "
            + required_rank.mention()
            + t" to execute this command for other users, but you only have the "
            + executing_rank.mention()
            + t"!",
        )


class StructureCountLimitReached(FeedbackError):
    def __init__(self, e: errors.StructureCountLimitReachedError) -> None:
        super().__init__(
            f"{e.structure_type.type_name.title()} Count Limit Reached",
            t"The limit of the total amount of {e.structure_type.type_name_plural} in this community has been reached, therefore you cannot add any more!",
        )


class SynNotUnique(FeedbackError):
    def __init__(self, e: errors.SynNotUniqueError) -> None:
        super().__init__(
            "Name Or Aliases Not Unique",
            t"The name or alias {e.given:,} has been specified multiple times, but they must be unique!",
        )


class AttributeValueSlotCountOutOfRange(FeedbackError):
    def __init__(self, e: errors.AttributeValueSlotCountOutOfRangeError) -> None:
        super().__init__(
            "Attribute Value Slot Count Out Of Range",
            t"The specified value has not enough or too many slots!",
            additional=t"The value {e.value:,} has {len(e.value):,} slots, but the {e.attribute.__class__.type_name.lower()} {e.attribute.name:,} requires between {e.attribute.min_slot_count:,} and {e.attribute.max_slot_count:,} slots in a value.",
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
            additional=t"`min_slot_count` must be at least {e.min_min}, while {'max_slot_count':,} must be at least 1, bigger than `min_slot_count` and below the community's limit of {e.max_max}.",
            paragraphs=(
                t"The following statement must be valid: `max_slot_count ≥ 1 and {e.min_min} ≤ min_slot_count ≤ max_slot_count ≤ {e.max_max}`.\n"
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
            t"You must at least have the "
            + rank_required.mention()
            + t", but your rank is only {my_rank:,}!",
        )


class NotUniqueStructureInMapping(FeedbackError):
    def __init__(
        self,
        structure: BaseStructure,
    ):
        super().__init__(
            f"{type(structure).type_name.title()} Not Unique",
            t"The "
            + layouts.mention(structure)
            + t" has been referenced multiple times as a key in the same mapping, but keys must be unique!",
        )


class DeletionAborted(FeedbackError):
    def __init__(self, structure: BaseStructure) -> None:
        super().__init__(
            "Deletion Aborted",
            t"The deletion of the {type(structure)} {structure:,} was aborted!",
            explicit_message_status=message.MessageStatus.WARNING,
        )


class SameName(FeedbackError):
    def __init__(self, structure: BaseStructure) -> None:
        super().__init__(
            "Already Specified Name",
            t"The "
            + layouts.mention(structure)
            + t" already has the same name as the one specified, therefore nothing changed!",
            explicit_message_status=message.MessageStatus.WARNING,
        )


class TaskNotGivenYet(FeedbackError):
    def __init__(self, community_user: CommunityUser, task: Task) -> None:
        super().__init__(
            "Task Not Given Yet",
            t"The + "
            + layouts.mention(community_user)
            + t" has not been given the "
            + layouts.mention(task)
            + t" yet, therefore it cannot be taken!",
        )


class TooLongSynError(FeedbackError):
    def __init__(self, e: errors.TooLongSynError) -> None:
        super().__init__(
            f"{e.syn.title()} Too Long",
            t"The {'name' if e.is_name else 'alias'} {text.shorten(e.syn):,} is too long!",
            additional=t"It is {len(e.syn):,} characters long, but the maximum allowed is {e.limit:,}.",
        )


class InvalidSlotStr(FeedbackError):
    def __init__(self, e: errors.InvalidSlotStrError) -> None:
        super().__init__(
            f"Invalid Slot String",
            t"The specified string {text.shorten(e.s):,} is invalid for the slot type {message.slot_type_to_name(e.slot_type):,}!",
            additional=t"The string must "
            + message.slot_type_to_must(e.slot_type)
            + t".",
        )


class CommunityUserAlreadyHasTask(FeedbackError):
    def __init__(self, community_user: CommunityUser, task: Task) -> None:
        super().__init__(
            "Task Already Given",
            t"The "
            + layouts.mention(community_user)
            + t" has already been given the "
            + layouts.mention(task)
            + t"!",
        )


class CollectionEntryLimitReached(FeedbackError):
    def __init__(self, e: errors.CollectionEntryLimitReachedError) -> None:
        super().__init__(
            f"Collection Entry Count Limit Reached",
            t"The limit of the total amount of collection entries has been surpassed!",
            additional=t"The specified collection has {e.count:,} entries, but the limit in this community is {e.limit:,}.",
        )


class CollectionEntryAliasLimitReached(FeedbackError):
    def __init__(self, e: errors.CollectionEntryAliasLimitReachedError) -> None:
        super().__init__(
            f"Collection Entry Alias Count Limit Reached",
            t"The limit of the total amount of collection entry aliases has been surpassed!",
            additional=t"The collection entry {e.collection_value:,} has {e.count:,} aliases, but the limit in this community is {e.limit:,}.",
        )


class NotAllTasksFitMinAndMaxSlotCountChanges(FeedbackError):
    def __init__(self, e: errors.NotAllTasksFitMinAndMaxSlotCountChangesError) -> None:
        strings = gist.table_to_gist_strings(
            tuple((task.name, v, str(len(v))) for task, v in e.wrong.items()),
            (
                "Task Name",
                f"Its Unfitting Value For {e.attribute.name!r}",
                "Value Slot Count",
            ),
        )

        assert strings

        urls = tuple(
            gist.create_gist(
                {f"Invalid Data #{str(i).zfill(len(str(len(strings))))}.md": file}
            )
            for i, file in enumerate(strings, 1)
        )

        assert urls

        super().__init__(
            f"Not All Tasks Fit Min And Max Slot Count",
            t"Not every value of the "
            + layouts.mention(e.attribute)
            + t" for all tasks in the "
            + layouts.mention(e.attribute.list)
            + t" match the new min and max slots criteria!",
            additional=t"In other words, these {Task.type_name_plural} do not have a value for the specified {type(e.attribute).type_name} with between {e.min:,} to {e.max:,} (inclusive) slots.",
            paragraphs=(
                t"Listed below are all values that don't fit:\n"
                + layouts._urls_additional(*urls),
            ),
            msg_kwargs={"suppress_embeds": True},
        )


class Unhandled(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            "Unhandled Error",
            t"An unhandled error has occurred!",
            additional=t"This is a bug. It will be logged internally and fixed soon.",  # touch some grass
        )


@t.overload
def create_feedback_from_structure_error(
    e: errors.SynNotUniqueError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.StructureCountLimitReachedError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.TooManyAliasesError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.TooLongSynError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.SynsAlreadyTakenError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.AttributeMinSlotsOrMaxSlotsOutOfRangeError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.InvalidSlotStrError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.CollectionEntryLimitReachedError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.CollectionEntryAliasLimitReachedError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.CollectionEntrySynNotUniqueError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.AttributeValueSlotCountOutOfRangeError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.CollectionEntryNotFoundError, **kwargs: t.Any
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.CommunityUserAlreadyHasTaskError,
    *,
    community_user: CommunityUser,
    task: Task,
    **kwargs: t.Any,
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.NotAllTasksFitMinAndMaxSlotCountChangesError,
    *,
    community_user: CommunityUser,
    task: Task,
    **kwargs: t.Any,
) -> FeedbackError:
    pass


@t.overload
def create_feedback_from_structure_error(
    e: errors.NotAllTasksFitMinAndMaxSlotCountChangesError, **kwargs: t.Any
) -> FeedbackError:
    pass


def create_feedback_from_structure_error[T: errors.BaseStructureError](
    e: T,
    *,
    community_user: CommunityUser | None = None,
    task: Task | None = None,
    **kwargs: t.Any,
) -> FeedbackError | T:
    if isinstance(e, errors.SynNotUniqueError):
        return SynNotUnique(e)
    if isinstance(e, errors.StructureCountLimitReachedError):
        return StructureCountLimitReached(e)

    # _validate_attribute_syns
    if isinstance(e, errors.TooManyAliasesError):
        return TooManyAliases(e)
    if isinstance(e, errors.TooLongSynError):
        return TooLongSynError(e)
    if isinstance(e, errors.SynsAlreadyTakenError):
        return SynsAlreadyTaken(e)

    if isinstance(e, errors.AttributeMinSlotsOrMaxSlotsOutOfRangeError):
        return AttributeMinSlotsOrMaxSlotsOutOfRange(e)

    # set_collection
    if isinstance(e, errors.InvalidSlotStrError):
        return InvalidSlotStr(e)
    if isinstance(e, errors.CollectionEntryLimitReachedError):
        return CollectionEntryLimitReached(e)
    if isinstance(e, errors.CollectionEntryAliasLimitReachedError):
        return CollectionEntryAliasLimitReached(e)
    if isinstance(e, errors.CollectionEntrySynNotUniqueError):
        return CollectionEntrySynNotUnique(e)

    if isinstance(e, errors.AttributeValueSlotCountOutOfRangeError):
        return AttributeValueSlotCountOutOfRange(e)

    if isinstance(e, errors.CollectionEntryNotFoundError):
        return CollectionEntryNotFound(e)

    if isinstance(e, errors.CommunityUserAlreadyHasTaskError):
        assert community_user is not None
        assert task is not None

        return CommunityUserAlreadyHasTask(community_user, task)

    if isinstance(e, errors.NotAllTasksFitMinAndMaxSlotCountChangesError):
        return NotAllTasksFitMinAndMaxSlotCountChanges(e)

    return e
