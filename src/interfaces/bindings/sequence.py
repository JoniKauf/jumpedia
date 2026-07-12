from domain.value_objects.attribute import AttributeSynStr
from domain.value_objects.field_slot import FieldSlotStr
from interfaces import dsls


def attribute_aliases(s: str | None) -> tuple[AttributeSynStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            AttributeSynStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(s)
        )
    )


def attributes(s: str | None) -> tuple[AttributeSynStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            AttributeSynStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(s)
        )
    )


def task_aliases(s: str | None) -> tuple[FieldSlotStr, ...]:
    return (
        ()
        if s is None
        else tuple(
            FieldSlotStr(alias)
            for alias in dsls.sequence.engine.SequenceEngine().eval(s)
        )
    )
