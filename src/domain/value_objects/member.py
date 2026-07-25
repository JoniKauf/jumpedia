from dataclasses import dataclass

lazy from domain.entities.member import MemberEntity


@dataclass(frozen=True, slots=True)
class OptionalMemberWrapper:
    value: MemberEntity | None

    def __str__(self) -> str:
        return (
            "<Deleted User>"
            if self.value is None
            else f"{self.value.name} ({self.value.member_id})"
        )
