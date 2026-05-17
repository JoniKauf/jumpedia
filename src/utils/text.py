def split_max(s: str, sep: str, max: int) -> list[str]:
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

    Returns
    -------
    list[str]
        List of split segments following greedy bounded splitting rules.

    Notes
    -----
    - This is not equivalent to str.split, textwrap.wrap, or regex-based splitting.
    - The algorithm uses a bounded lookahead window (max + len(sep)) to detect
      separators for improved split alignment.
    """

    if not sep:
        raise ValueError("empty separator")

    if not max:
        raise ValueError("max lower or equal to 0")

    l = len(s)
    sl = len(sep)

    if not l:
        return [""]

    if l <= max:
        return [s]

    res: list[str] = []
    start: int = 0

    while True:
        end = start + max

        if end >= l:
            res.append(s[start:end])

            return res

        pos = s[start : end + sl].rfind(sep)

        if pos == -1:
            res.append(s[start:end])
            start = end
        else:
            pos += start
            res.append(s[start:pos])
            start = pos + sl

        i += 1
