import typing as t

# This was coded by JoniKauf, but he was too lazy to release it as its own 
# repository yet.

def split_into_chunks_prefer_seperator(
    s: str, sep: str, max: int, min: int = 0
) -> list[str]:
    """
    Greedy bounded string splitter with separator-preferred backtracking.

    Splits a string into segments constrained by a maximum length. The algorithm
    prefers to split at occurrences of `sep` within a bounded lookahead window,
    but falls back to hard cuts when no separator is found.

    The process is greedy, single-pass, and processes the string from left to right.

    Key properties
    --------------
    - Each emitted segment satisfies: len(segment) <= max (except final remainder).
    - Separator positions are used only as split anchors and are not emitted.
    - The algorithm is deterministic and does not perform global optimization.

    Parameters
    ----------
    s : str
        Input string to split.
    sep : str
        Non-empty separator used to prefer split positions.
    max : int
        Maximum allowed segment length (> 0).
    min : int
        Minimum allowed segment length (except last).

    Returns
    -------
    list[str]
        List of split segments following greedy bounded splitting rules.

    Notes
    -----
    - This is not equivalent to str.split, textwrap.wrap, or regex-based splitting.
    - The algorithm uses a bounded lookahead window (max + len(sep)) to detect separators for improved split alignment.
    """
    if not sep:
        raise ValueError("empty separator")

    if min < 0:
        raise ValueError("min lower than 0")

    if min > max:
        raise ValueError("min greater than max")

    if max == 0:
        raise ValueError("max equal to 0")

    l = len(s)
    sl = len(sep)

    if l == 0:
        return [""]

    if l <= max:
        return [s]

    res: list[str] = []
    start: int = 0

    while True:
        end = start + max

        if end >= l:
            res.append(s[start:])
            return res

        search_start = start + min
        search_end = end + sl

        pos = s[search_start:search_end].rfind(sep)

        if pos == -1:
            res.append(s[start:end])
            start = end
        else:
            pos += search_start
            res.append(s[start:pos])
            start = pos + sl


def table_data_to_str(
    headers: t.Iterable[str], rows: t.Iterable[t.Iterable[str]], max_table_size: int
) -> list[str]:
    HEADERS: t.Final[tuple[str, ...]] = tuple(headers)

    if not headers:
        raise ValueError("Empty headers")

    COL_COUNT = len(HEADERS)

    del headers

    VALIDATED_ROW_BASE: t.Final[list[str]] = [""] * COL_COUNT
    validated_rows: list[list[str]] = []

    for row in rows:
        validated_row: list[str] = VALIDATED_ROW_BASE.copy()
        i: int = -1

        for i, cell in enumerate(row):
            if i >= COL_COUNT:
                raise ValueError("Row not same length as headers")

            validated_row[i] = cell

        if i + 1 != COL_COUNT:
            raise ValueError("Row not same length as headers")

        validated_rows.append(validated_row)

    if not validated_rows:
        return []

    DELIM = " | "
    SPLITTER_DELIM = "-+-"
    DELIM_LEN = 3

    ROW_COUNT: t.Final[int] = len(validated_rows)
    SUMMED_DELIM_LEN_PER_ROW: t.Final[int] = (COL_COUNT - 1) * DELIM_LEN
    BASE_MAX_COL_LENGTHS: t.Final[tuple[int, ...]] = tuple(len(h) for h in HEADERS)

    # Header content length + delimiters + the same for the splitter row + 1 newline.
    if (sum(BASE_MAX_COL_LENGTHS) + SUMMED_DELIM_LEN_PER_ROW) * 2 + 1 > max_table_size:
        raise ValueError("Header + splitter row already bigger than limit")

    tables: list[str] = []
    start_idx: int = 0

    while start_idx < ROW_COUNT:
        max_col_lengths: tuple[int, ...] = BASE_MAX_COL_LENGTHS
        end_idx: int = start_idx

        for row in validated_rows[start_idx:]:
            test_max_col_lengths = tuple(
                max(len(cell), current_max)
                for cell, current_max in zip(row, max_col_lengths, strict=True)
            )

            row_count: int = end_idx - start_idx + 1

            current_char_count = (
                sum(test_max_col_lengths) + SUMMED_DELIM_LEN_PER_ROW + 1
            ) * (row_count + 2) - 1

            if current_char_count > max_table_size:
                break

            max_col_lengths = test_max_col_lengths
            end_idx += 1

            if current_char_count == max_table_size:
                break

        if end_idx == start_idx:
            raise ValueError(
                "Could not fit a single row into table with specified limit"
            )

        header_str = DELIM.join(
            h.ljust(max_col_lengths[i]) for i, h in enumerate(HEADERS)
        )
        splitter_str = SPLITTER_DELIM.join(
            "-" * max_col_lengths[i] for i in range(COL_COUNT)
        )
        rows_str = "\n".join(
            DELIM.join(cell.ljust(max_col_lengths[i]) for i, cell in enumerate(row))
            for row in validated_rows[start_idx:end_idx]
        )

        tables.append(f"{header_str}\n{splitter_str}\n{rows_str}")

        start_idx = end_idx

    return tables
