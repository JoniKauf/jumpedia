from domain.entities.user import CommunityUserEntity, UserEntity
from domain.enums.rank import CommunityRank, MetaRank, ServerRank
from domain import errors


class PermissionService:
    @staticmethod
    def ensure_meta_rank(meta_rank: MetaRank, required: MetaRank) -> None:
        if meta_rank.value < required.value:
            raise errors.NotAllowed(meta_rank, required)

    @staticmethod
    def ensure_community_rank(
        community_rank: CommunityRank, meta_rank: MetaRank, required: CommunityRank
    ) -> None:
        if not meta_rank and community_rank.value < required.value:
            raise errors.NotAllowed(community_rank, required)

    @staticmethod
    def ensure_server_rank(
        server_rank: ServerRank, meta_rank: MetaRank, required: ServerRank
    ) -> None:
        if not meta_rank and server_rank.value < required.value:
            raise errors.NotAllowed(server_rank, required)
