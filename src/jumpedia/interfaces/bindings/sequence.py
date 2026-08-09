from jumpedia.domain.value_objects.attribute import AttributeSynStr
from jumpedia.domain.value_objects.field_slot import FieldSlotStr
from jumpedia.domain.value_objects.string import RealStr
from jumpedia.interfaces import dsls


# attribute_aliases, attributes and yield_ technically share the same
# code but might evolve differently. Keep them seperate.
def attribute_aliases(s: str | None) -> tuple[AttributeSynStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            AttributeSynStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(str(RealStr(s)))
        )
    )


def attributes(s: str | None) -> tuple[AttributeSynStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            AttributeSynStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(str(RealStr(s)))
        )
    )


def yield_(s: str | None) -> tuple[AttributeSynStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            AttributeSynStr(syn)
            for syn in dsls.sequence.engine.SequenceEngine().eval(str(RealStr(s)))
        )
    )


def task_aliases(s: str | None) -> tuple[FieldSlotStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            FieldSlotStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(str(RealStr(s)))
        )
    )
