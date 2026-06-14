from domain.entities.base import BaseEntity
from domain.enums.rank import MetaRank
from domain.types.user import UserID
from domain.value_objects.user import UserName


class UserEntity(BaseEntity[UserID]):
    def __init__(
        self, id: UserID, name: UserName, rank: MetaRank = MetaRank.DEFAULT
    ) -> None:
        super().__init__(id)

        self.name = name
        self.meta_rank = rank

    @property
    def name(self) -> UserName:
        return self._name

    @name.setter
    def name(self, value: UserName) -> None:
        self._name = value

    @property
    def meta_rank(self) -> MetaRank:
        return self._rank

    @meta_rank.setter
    def meta_rank(self, value: MetaRank) -> None:
        self._rank = value
