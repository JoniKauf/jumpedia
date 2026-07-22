from dataclasses import dataclass

from domain.entities.community import CommunityEntity
from domain.errors import business
from domain.typing.collection_entry import AbstractCollectionT, FrozenCollectionT



@dataclass(frozen=True, slots=True, eq=False)
class CollectionBuildService:
    def build_collection(self, collection: AbstractCollectionT, community: CommunityEntity) -> FrozenCollectionT:
        if len(collection) > community.limits.collection_entry_count_max:
            raise business.CountLimitReached(
                community.limits.collection_entry_count_max,
                CollectionEntryEntity,
            )

        for entry in entire_collection:
            if len(entry[1]) > community.limits.collection_entry_alias_count_max:
                raise business.AliasCountLimitReached(
                    community.limits.collection_entry_alias_count_max,
                    entry[0],
                    entry[1],
                )