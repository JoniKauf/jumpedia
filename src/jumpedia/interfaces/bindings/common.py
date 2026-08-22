from jumpedia.domain.value_objects.string import RealStr


def build_dsl_input(s: str) -> str:
    return RealStr.clean(
        s,
        clean_whitespace=False,
        replace_quotation_marks=True,
        remove_non_printables=True,
        normalize_unicode_codepoints=True,
        validate_final_string=True,
    )
