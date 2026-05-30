from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain import errors


class PermissionService:
    def __init__(self) -> None:
        pass
    
    def ensure_meta_rank(self, meta_rank: MetaRank, required: MetaRank) -> None:
        if meta_rank.value < required.value:
            raise errors.NotAllowed(meta_rank, required)

    def ensure_community_rank(
        self, community_rank: CommunityRank, meta_rank: MetaRank, required: CommunityRank
    ) -> None:
        if not meta_rank and community_rank.value < required.value:
            raise errors.NotAllowed(community_rank, required)

    def ensure_server_rank(
        self, server_rank: ServerRank, meta_rank: MetaRank, required: ServerRank
    ) -> None:
        if not meta_rank and server_rank.value < required.value:
            raise errors.NotAllowed(server_rank, required)
