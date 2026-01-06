from operator import add
from string.templatelib import Template
from typing import Any, Mapping, Sequence

from discord_.errors import FeedbackError
from structures import BaseStructure, errors
from utils import text
from utils.rank import AnyRankT


class StructureNotFoundViaSynFeedbackError(FeedbackError):
    def __init__(
        self, syn: str, structure_type: type[BaseStructure], only_name: bool = False
    ) -> None:
        super().__init__(
            f"{structure_type.type_name.title()} Not Found",
            t"The specified {structure_type.type_name} with the name {"" if only_name else "or alias "}{syn:c} could not be found!",
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
            t"The specified {names[many].lower():p} or {aliases[many].lower():p} ({syns:c}) {are[many].lower():p} already taken!",
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
            t"This server is already connected to a community ({e.community.name:c})!",
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
            t"The limit of the total amount of {e.structure_type.type_name.lower()}s in this community has been reached, therefore you cannot add any more!",
        )


class SynNotUniqueFeedbackError(FeedbackError):
    def __init__(self, e: errors.NotUniqueStringError) -> None:
        super().__init__(
            "Name Or Aliases Not Unique",
            t"The name or alias {e.given:c} has been specified multiple times, but they must be unique!",
        )


class AttributeValueSlotCountOutOfRangeFeedbackError(FeedbackError):
    def __init__(self, e: errors.AttributeValueSlotCountOutOfRangeError) -> None:
        super().__init__(
            "Attribute Value Slot Count Out Of Range",
            t"The specified value has not enough or too many slots!",
            additional=t"The value {list(e.value):c} has {len(e.value):c} slots, but the {e.attribute.__class__.type_name.lower()} {e.attribute.name:c} requires between {e.attribute.min_slots:c} and {e.attribute.max_slots:c} slots in a value.",
        )


class CollectionEntryNotFoundFeedbackError(FeedbackError):
    def __init__(self, e: errors.CollectionEntryNotFoundError) -> None:
        super().__init__(
            "Collection Entry Not Found",
            t"The specified collection entry {e.real_slot:c} could not be found in the collection of the {e.collection.attribute.__class__.type_name} {e.collection.attribute.name:c}!",
        )


class CollectionEntrySynNotUniqueFeedbackError(FeedbackError):
    def __init__(self, e: errors.CollectionEntrySynNotUniqueError) -> None:
        super().__init__(
            "Collection Entry Value Or Alias Not Unique",
            t"The collection entry's value or alias {e.duplicate:c} has been specified multiple times, but they must be unique!",
        )


class EmptyStringFeedbackError(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            "Empty String",
            t'You entered an empty or whitespace-only string (`""`), which is not allowed!',
        )

class DoubleBacktickFeedbackError(FeedbackError):
    def __init__(self) -> None:
        super().__init__(
            "Double Backtick",
            t'You entered a string that contains a double backtick (``` ```), which is not allowed!',
            additional=t"The reason it is not allowed is because otherwise it would be impossible to correctly format such messages inside Discord."
        )


class AttributeMinSlotsOrMaxSlotsOutOfRangeFeedbackError(FeedbackError):
    def __init__(self, e: errors.AttributeMinSlotsOrMaxSlotsOutOfRangeError) -> None:
        super().__init__(
            "Slot Limits Out Of Range",
            t"The min or max slot count specified is invalid!",
            additional=t"`min_slots` must be at least {e.min_min}, while `max_slots` must be at least 1, bigger than `min_slots` and below the community's limit of {e.max_max}.",
            paragraphs=(
                t"The following statement must be valid: `max_slots ≥ 1 and {e.min_min} ≤ min_slots ≤ max_slots ≤ {e.max_max}`.\n"
                t"The values you entered result in this statement: {e.max} ≥ 1 and {e.min_min} ≤ {e.min} ≤ {e.max} ≤ {e.max_max:c}.",
            ),
        )


class TooManyAliasesFeedbackError(FeedbackError):
    def __init__(self, e: errors.TooManyAliasesError) -> None:
        super().__init__(
            "Too Many Aliases",
            t"The amount of alises specified is too high. {e.aliases}`!",
        )
