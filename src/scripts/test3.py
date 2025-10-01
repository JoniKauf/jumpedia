import re


class ArgParser:
    # From https://www.fileformat.info/info/unicode/block/general_punctuation/utf8test.htm
    CLEAN_MAP: dict[str, str] = {"'": "‘’‚‛", '"': "”“„‟"}

    def __init__(self) -> None:
        pass

    def _clean(self, s: str, /) -> str:
        s = s.strip()

        for k, v in self.__class__.CLEAN_MAP.items():
            s = re.sub(rf"[{re.escape(v)}]", k, s)

        return s

    def parse_args(self, s: str, /) -> list[str]:
        s = self._clean(s)

        result: list[str] = []
        in_quotes: bool = False
        in_escape: bool = False
        current_arg: list[str] = []
        prev_c: str = ""
        COUNT = len(s)

        for i, c in enumerate(s):
            if in_escape:
                if c not in '\\"':
                    raise ValueError('\\ not followed by " or \\')

                current_arg.append(c)
                in_escape = False

            elif not in_escape and c == "\\":
                in_escape = True

            elif c == '"':
                if in_quotes:
                    result.append("".join(current_arg))
                    current_arg = []

                    if i < COUNT - 1 and not s[i + 1].isspace():
                        raise ValueError('Closing " not proceded by whitespace')
                else:
                    if prev_c and not prev_c.isspace():
                        raise ValueError('Opening " not preceded by whitespace')

                in_quotes = not in_quotes

            else:
                if in_quotes:
                    current_arg.append(c)
                else:
                    if c.isspace():
                        if not prev_c.isspace():
                            result.append("".join(current_arg))
                            current_arg = []
                    else:
                        current_arg.append(c)

            prev_c = c

        if in_escape:
            raise ValueError("Not escaped final \\")

        if in_quotes:
            raise ValueError("Not closed quotation mark")

        if current_arg:
            result.append("".join(current_arg))

        return result


parser = ArgParser()

while True:
    try:
        result = parser.parse_args(input("Input: "))
    except ValueError as e:
        result = f"Error raised: {e.args[0]}"

    print("Result:", result, "Lengths:", [len(s) for s in result])
