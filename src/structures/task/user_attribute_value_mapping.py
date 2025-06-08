from dataclasses import dataclass
from database import queries, typed
from structures.attributes.user_attribute import UserAttribute
from structures.task.abstract_attribute_value_mapping import AbstractAttributeValueMapping
from structures.task.task_attribute_value_mapping import TaskAttributeValueMappingAttributeT

type UserAttributeValueMappingAttributeT = TaskAttributeValueMappingAttributeT | UserAttribute

@dataclass(frozen=True, kw_only=True)
class UserAttributeValueMapping(AbstractAttributeValueMapping[UserAttributeValueMappingAttributeT]):
    """Task User Attribute Value Collection"""

    user_id: int

    def __post_init__(self) -> None:
        super().__post_init__()
        self._add_user_attributes()

    def _add_user_attributes(self) -> None:
        h = queries.ArgHelper()

        with queries.connected() as (conn, cursor):
            cursor.execute(f"""
                SELECT *
                FROM user_attribute_task_value
                WHERE 
                    task_id = {h|self.task.id}
                    AND user_id = {h|self.user_id}
            """, h.steal())

            result: typed.ManyTableRowT = cursor.fetchall()

        # Get all attributes specified for this task
        attributes = self.task.list.get_user_attributes(
            lambda h: f"id in ({','.join((h|(row['user_attribute_id'])) for row in result)})"
        )

        attribute_lookup: dict[int, UserAttribute] = {
            attr.id: attr for attr in attributes
        }

        for row in result:
            try:
                attr = attribute_lookup.pop(row['user_attribute_id'])
            except KeyError:
                raise fbe.TemporaryFeedbackError("Data changed")
            
            val: list[AttributeValueTypeT] = pickle.loads(row['value'])
            
            self.mapping[attr] = val 

        if attribute_lookup:
            raise fbe.TemporaryFeedbackError("Data changed")
        