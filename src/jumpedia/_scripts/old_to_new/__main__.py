import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from jumpedia._scripts.old_to_new import old
from jumpedia.db import models as new
from jumpedia.db.session import get_session
from jumpedia.domain.enums.attribute import AttributeKind, AttributeType
from jumpedia.domain.value_objects.attribute import KindedAttributeDefaultProperties
from jumpedia.domain.value_objects.community import CommunityLimits
from jumpedia.domain.value_objects.string import NormHash, RealStr

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OldDatabase:
    communities: tuple[old.CommunityModel, ...]
    servers: tuple[old.ServerModel, ...]
    jumpedia_users: tuple[old.JumpediaUserModel, ...]
    lists: tuple[old.ListModel, ...]
    community_users: tuple[old.CommunityUserModel, ...]
    attributes: tuple[old.AttributeModel, ...]
    attribute_aliases: tuple[old.AttributeAliasModel, ...]
    attribute_collection_entries: tuple[old.AttributeCollectionEntryModel, ...]
    attribute_collection_entry_aliases: tuple[
        old.AttributeCollectionEntryAliasModel, ...
    ]
    tasks: tuple[old.TaskModel, ...]
    task_aliases: tuple[old.TaskAliasModel, ...]
    task_attribute_values: tuple[old.TaskAttributeValueModel, ...]
    community_user_tasks: tuple[old.CommunityUserTaskModel, ...]
    community_user_task_attribute_values: tuple[
        old.CommunityUserTaskAttributeValueModel, ...
    ]


def load_old_database(session: Session) -> OldDatabase:
    return OldDatabase(
        communities=tuple(session.scalars(select(old.CommunityModel)).all()),
        servers=tuple(session.scalars(select(old.ServerModel)).all()),
        jumpedia_users=tuple(session.scalars(select(old.JumpediaUserModel)).all()),
        lists=tuple(session.scalars(select(old.ListModel)).all()),
        community_users=tuple(session.scalars(select(old.CommunityUserModel)).all()),
        attributes=tuple(session.scalars(select(old.AttributeModel)).all()),
        attribute_aliases=tuple(session.scalars(select(old.AttributeAliasModel)).all()),
        attribute_collection_entries=tuple(
            session.scalars(select(old.AttributeCollectionEntryModel)).all()
        ),
        attribute_collection_entry_aliases=tuple(
            session.scalars(select(old.AttributeCollectionEntryAliasModel)).all()
        ),
        tasks=tuple(session.scalars(select(old.TaskModel)).all()),
        task_aliases=tuple(session.scalars(select(old.TaskAliasModel)).all()),
        task_attribute_values=tuple(
            session.scalars(select(old.TaskAttributeValueModel)).all()
        ),
        community_user_tasks=tuple(
            session.scalars(select(old.CommunityUserTaskModel)).all()
        ),
        community_user_task_attribute_values=tuple(
            session.scalars(select(old.CommunityUserTaskAttributeValueModel)).all()
        ),
    )


def main() -> None:
    with get_session() as session:
        logger.info("Loading old db data...")
        old_db = load_old_database(session)

        logger.info(new.UserModel.__name__)
        session.add_all(
            new.UserModel(
                user_id=user.id,
                name=RealStr(user.raw_name[:32]),
                meta_rank=0 if user.power == 0 else 1 if user.power == 100 else 2,
            )
            for user in old_db.jumpedia_users
        )
        session.flush()

        logger.info(new.CommunityModel.__name__)
        # Ignore limits for now
        # Add default_selected_list_id after creation
        session.add_all(
            new.CommunityModel(
                community_id=community.id,
                name=(name := RealStr(community.real_name)),
                name_hash=NormHash(name),
                default_selected_list_id=None,
                community_list_count_max=CommunityLimits.DEFAULT.community_list_count_max,
                list_attribute_count_max=CommunityLimits.DEFAULT.list_attribute_count_max,
                list_task_count_max=CommunityLimits.DEFAULT.list_task_count_max,
                attribute_alias_count_max=CommunityLimits.DEFAULT.attribute_alias_count_max,
                field_slot_count_max=CommunityLimits.DEFAULT.field_slot_count_max,
                collection_entry_count_max=CommunityLimits.DEFAULT.collection_entry_count_max,
                collection_entry_alias_count_max=CommunityLimits.DEFAULT.collection_entry_alias_count_max,
            )
            for community in old_db.communities
        )
        session.flush()

        logger.info(new.ServerModel.__name__)
        session.add_all(
            new.ServerModel(server_id=server.id, community_id=server.community_id)
            for server in old_db.servers
        )
        session.flush()

        logger.info(new.ListModel.__name__)
        session.add_all(
            new.ListModel(
                list_id=lst.id,
                community_id=lst.community_id,
                name=(name := RealStr(lst.real_name)),
                name_hash=NormHash(name),
            )
            for lst in old_db.lists
        )
        session.flush()

        logger.info(new.CommunityModel.default_selected_list_id)
        for community in old_db.communities:
            if community.default_selected_list_id is not None:
                session.get(
                    new.CommunityModel,
                    community.id,
                ).default_selected_list_id = community.default_selected_list_id  # type: ignore
        session.flush()

        logger.info(new.MemberModel.__name__)
        session.add_all(
            new.MemberModel(
                member_id=community_user.id,
                community_id=community_user.community_id,
                user_id=community_user.jumpedia_user_id,
                community_rank=community_user.power // 100,
                selected_list_id=community_user.selected_list_id,
            )
            for community_user in old_db.community_users
        )
        session.flush()

        logger.info(new.AttributeModel.__name__)
        session.add_all(
            new.AttributeModel(
                attribute_id=attr.id,
                list_id=attr.list_id,
                name=(name := RealStr(attr.real_name)),
                name_hash=NormHash(name),
                type=(
                    AttributeType.TASK if attr.type_id == 0 else attr.type_id
                ),  # Turn Static into Task
                kind=(
                    None if attr.kind is None else attr.kind + 1
                ),  # Previously started at 0
                slot_type=attr.slot_type + 1,  # Previously used index, so started at 0
                min_slot_count=attr.min_slot_count,
                max_slot_count=attr.max_slot_count,
                unique_slots=attr.kind
                in (AttributeKind.ALIAS,),  # Only unique by default is Alias
                position=attr.position
                + (
                    3 if attr.position > 3 else 0
                ),  # Offset by 3 so new ones have space; simply put them at 4-6 pos
            )
            for attr in old_db.attributes
        )
        session.flush()

        logger.info(new.AttributeModel.kind)
        # Add mew kinds
        for lst in old_db.lists:
            session.add_all(
                new.AttributeModel(
                    # id autogenerated
                    list_id=lst.id,
                    name_hash=default.name.hash,
                    name=default.name.real,
                    type=default.kind.type,  # Turn Static into Task
                    kind=default.kind,  # Previously started at 0
                    slot_type=default.field_config.slot_type,  # Previously used index, so started at 0
                    min_slot_count=default.field_config.min_slot_count,
                    max_slot_count=default.field_config.max_slot_count,
                    unique_slots=default.field_config.unique_slots,
                    position=default.position.value,  # Offset non kinded by 3 so new kinded have space
                )
                for default in KindedAttributeDefaultProperties.DEFAULTS
                if default.kind > AttributeKind.ALIAS
            )
        session.flush()

        logger.info(new.AttributeAliasModel.__name__ + " lookup")
        attr_id_to_aliases: dict[int, list[old.AttributeAliasModel]] = {}

        for alias in old_db.attribute_aliases:
            attr_id_to_aliases.setdefault(alias.attribute_id, []).append(alias)

        logger.info(new.AttributeAliasModel.__name__)
        session.add_all(
            new.AttributeAliasModel(
                attribute_id=alias.attribute_id,
                index=i,
                list_id=alias.list_id,
                alias=(a := RealStr(alias.real_alias)),
                alias_hash=NormHash(a),
            )
            for attr in old_db.attributes
            for i, alias in enumerate(attr_id_to_aliases.get(attr.id, ()))
        )
        session.flush()

        logger.info(new.CollectionEntryModel.__name__)
        session.add_all(
            new.CollectionEntryModel(
                collection_entry_id=entry.id,
                attribute_id=entry.attribute_id,
                index=entry.index,
                value=(slot := RealStr(entry.slot_slot)),
                value_hash=NormHash(slot),
            )
            for entry in old_db.attribute_collection_entries
        )
        session.flush()

        logger.info(new.CollectionEntryAliasModel.__name__ + " lookup")
        collection_entry_id_to_aliases: dict[
            int, list[old.AttributeCollectionEntryAliasModel]
        ] = {}

        for alias in old_db.attribute_collection_entry_aliases:
            collection_entry_id_to_aliases.setdefault(
                alias.attribute_collection_entry_id, []
            ).append(alias)

        logger.info(new.CollectionEntryAliasModel.__name__)
        session.add_all(
            new.CollectionEntryAliasModel(
                collection_entry_id=alias.attribute_collection_entry_id,
                index=i,
                attribute_id=alias.attribute_id,
                alias=(a := RealStr(alias.slot_alias)),
                alias_hash=NormHash(a),
            )
            for entry in old_db.attribute_collection_entries
            for i, alias in enumerate(collection_entry_id_to_aliases.get(entry.id, ()))
        )
        session.flush()

        logger.info(new.TaskModel.__name__)
        session.add_all(
            new.TaskModel(
                task_id=task.id,
                list_id=task.list_id,
                name=(name := RealStr(task.slot_name)),
                name_hash=NormHash(name),
            )
            for task in old_db.tasks
        )
        session.flush()

        logger.info(new.TaskAliasModel.__name__ + " lookup")
        task_id_to_aliases: dict[int, list[old.TaskAliasModel]] = {}

        for alias in old_db.task_aliases:
            task_id_to_aliases.setdefault(alias.task_id, []).append(alias)

        logger.info(new.TaskAliasModel.__name__)
        session.add_all(
            new.TaskAliasModel(
                task_id=alias.task_id,
                index=i,
                list_id=alias.list_id,
                alias=(a := RealStr(alias.slot_alias)),
                alias_hash=NormHash(a),
            )
            for task in old_db.tasks
            for i, alias in enumerate(task_id_to_aliases.get(task.id, ()))
        )
        session.flush()

        logger.info(new.FieldSlotModel.__name__)
        session.add_all(
            new.FieldSlotModel(
                task_id=value.task_id,
                attribute_id=value.attribute_id,
                index=value.index,
                slot=(slot := RealStr(value.slot_slot)),
                slot_hash=NormHash(slot),
            )
            for value in old_db.task_attribute_values
        )
        session.flush()

        logger.info(new.MemberTaskModel.__name__)
        session.add_all(
            new.MemberTaskModel(
                member_task_id=community_user_task.id,
                member_id=community_user_task.community_user_id,
                task_id=community_user_task.task_id,
                given_by=None,
            )
            for community_user_task in old_db.community_user_tasks
        )
        session.flush()

        logger.info(new.MemberFieldSlotModel.__name__)
        session.add_all(
            new.MemberFieldSlotModel(
                member_task_id=value.community_user_task_id,
                attribute_id=value.attribute_id,
                index=value.index,
                slot=(slot := RealStr(value.slot_slot)),
                slot_hash=NormHash(slot),
            )
            for value in old_db.community_user_task_attribute_values
        )
        session.flush()


if __name__ == "__main__":
    main()
