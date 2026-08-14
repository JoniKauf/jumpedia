from jumpedia.domain.value_objects.string import RealStr


def build_dsl_input(s: str) -> str:
    s = RealStr.replace_quotation_marks(s)
    s = RealStr.remove_non_printables(s)
    s = RealStr.normalize_unicode_codepoints(s)

    RealStr.validate_final_string(s)

    return s
