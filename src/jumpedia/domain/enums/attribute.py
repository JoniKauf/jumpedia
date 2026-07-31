import decimal
import enum
import typing as t

from jumpedia.domain.errors.internal import UndefinedTypeForKind

lazy from jumpedia.domain.typing.attribute import (
    AnyAttributeTypeT,
    NoneKindedAttributeT,
    SlotTypeT,
    TaskAttributeTypeT,
    TaskKindedAttributeT,
    UserAttributeTypeT,
    UserKindedAttributeT,
)
from jumpedia.infrastructure.types.classproperty import cached_classproperty


@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeType(enum.IntEnum):
    TASK = 1
    USER = 2

    @t.overload
    def as_set(self: TaskAttributeTypeT) -> t.AbstractSet[TaskAttributeTypeT]:
        pass

    @t.overload
    def as_set(self: UserAttributeTypeT) -> t.AbstractSet[UserAttributeTypeT]:
        pass

    def as_set(  # pyright: ignore[reportInconsistentOverload]
        self,
    ) -> t.AbstractSet[t.Self]:
        return {self}

    @cached_classproperty
    def ALL(cls) -> t.AbstractSet[AnyAttributeTypeT]:
        return {cls.TASK, cls.USER}


@enum.verify(enum.UNIQUE)
class AttributeKind(enum.IntEnum):
    """The kind of an attribute.

    A kind can be thought of as a subtype in some ways. Any non-special attribute has
    the Attribute Kind `NONE`. Any special attribute only exists once and which of
    special attributes it is, is determined by its kind. Every kind is also either task
    or user type bound, except `NONE`, because it just represents any non-special
    attribute. Therefore we can differentiate between 3 different categories:
    - None kinded
    - Task kinded
    - User kinded

    Invariant: A kind must either be `NONE` or the attribute it belongs to must have
    the matching attribute type.
    """

    # Internally we work with the enum member NONE because it is
    # way nicer to work with instead of union with None everywhere.
    # In the database NONE here is actually NULL. This lets us
    # enforce a unique constraint on the kind, since NULL must not
    # be unique where a unique constraint is enforced.
    # Currently no kinded attributes have collections!
    NONE = 0

    # 1 to 8: Task Attribute Kinds
    ID = 1
    NAME = 2
    ALIAS = 3
    CREATED_AT = 4

    # 9 to 16: User Attribute Kinds
    GIVEN_AT = 9
    GIVEN_BY = 10

    @property
    def type(self) -> AnyAttributeTypeT:
        """Will throw for NONE because NONE can be both!"""

        match self:
            case (
                AttributeKind.ID
                | AttributeKind.NAME
                | AttributeKind.ALIAS
                | AttributeKind.CREATED_AT
            ):
                return AttributeType.TASK

            case AttributeKind.GIVEN_AT | AttributeKind.GIVEN_BY:
                return AttributeType.USER

            case AttributeKind.NONE:
                raise UndefinedTypeForKind(self)

            case _:
                t.assert_never(self)

    @cached_classproperty
    def NONE_KINDED(cls) -> t.AbstractSet[NoneKindedAttributeT]:
        return frozenset(t.get_args(NoneKindedAttributeT.__value__))

    @cached_classproperty
    def TASK_KINDED(cls) -> t.AbstractSet[TaskKindedAttributeT]:
        return frozenset(t.get_args(TaskKindedAttributeT.__value__))

    @cached_classproperty
    def USER_KINDED(cls) -> t.AbstractSet[UserKindedAttributeT]:
        return frozenset(t.get_args(UserKindedAttributeT.__value__))

    @cached_classproperty
    def NONE_OR_TASK_KINDED(
        cls,
    ) -> t.AbstractSet[NoneKindedAttributeT | TaskKindedAttributeT]:
        return cls.NONE_KINDED | cls.TASK_KINDED

    @cached_classproperty
    def NONE_OR_USER_KINDED(
        cls,
    ) -> t.AbstractSet[NoneKindedAttributeT | UserKindedAttributeT]:
        return cls.NONE_KINDED | cls.USER_KINDED

    @cached_classproperty
    def ALL(cls) -> t.AbstractSet[AttributeKind]:
        cls = t.cast(type[t.Self], cls)
        return frozenset(cls)


@enum.verify(enum.UNIQUE, enum.CONTINUOUS)
class AttributeSlotType(enum.IntEnum):
    BOOLEAN = 1
    INTEGER = 2
    DECIMAL = 3
    STRING = 4

    @property
    def python_type(self) -> type[SlotTypeT]:
        match self:
            case AttributeSlotType.BOOLEAN:
                return bool
            case AttributeSlotType.INTEGER:
                return int
            case AttributeSlotType.DECIMAL:
                return decimal.Decimal
            case AttributeSlotType.STRING:
                return str
            case _:
                t.assert_never(self)
