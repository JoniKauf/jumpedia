from domain.enums.concept import Concept
from interfaces.message.formattable import FormattableForms


def cog_concept_to_group_name(concept: Concept, *, plural: bool) -> str:
    forms = FormattableForms.from_formattable(concept)

    return (forms.plural if plural else forms.singular).replace(" ", "_")
