if __name__ != '__main__':
    raise SyntaxError()

from decimal import Decimal
import re
import datetime as dt

_TIMEDELTA_PARSE_PATTERN = re.compile(r'''
    ^                     # String start
    ([-+])?               # [Group 1: Optional '-' or '+' sign]
    \s*                   # Whitespace 0 to ∞ times
    (?:                   # Group without capturing:
        ([0-9]+)              # [Group 2: Any digit 0 to ∞ times]
        \s*                   # Whitespace 0 to ∞ times
        (d|days?)             # [Group 3: 'd', 'day' or 'days']
    )?                    # End group, its insides must either fully match or not exist at all
    \s*                   # Whitespace 0 to ∞ times
    (?:                   # Group without capturing:
        ([0-1]?[0-9]|2[0-3])  # [Group 4: 0 to 23] with optional leading 0 for single digit numbers
        \s*                   # Whitespace 0 to ∞ times
        (h|hrs?|hours?)        # [Group 5: 'h', 'hr', 'hrs', 'hour' or 'hours']
    )?                    # End group, its insides must either fully match or not exist at all
    \s*                   # Whitespace 0 to ∞ times
    (?:                   # Group without capturing:
        ([0-5]?[0-9])         # [Group 6: 0 to 59] with optional leading 0 for single digit numbers
        \s*                   # Whitespace 0 to ∞ times
        (m|mins?|minutes?)    # [Group 7: 'm', 'min', 'mins', 'minute' or 'minutes']
    )?                    # End group, its insides must either fully match or not exist at all
    \s*                   # Whitespace 0 to ∞ times
    (?:                   # Group without capturing:
        (                     # [Group 8: 
            [0-5]?[0-9]           # 0 to 59, with optional leading 0 for single digit numbers
            (?:\.[0-9]*)?         # followed by optional: '.' followed by any digits 0 to ∞ times
        )                     # ]
        \s*                   # Whitespace 0 to ∞ times
        (s|secs?|seconds?)    # [Group 9: 's', 'sec', 'secs', 'second' or 'seconds']
    )?                    # End group, its insides must either fully match or not exist at all
    $                     # String end
''', re.VERBOSE | re.IGNORECASE)

def _parse_timedelta(s: str) -> dt.timedelta:
    match = _TIMEDELTA_PARSE_PATTERN.match(s.strip())

    if match is None:
        raise ValueError("Invalid timedelta format")

    # Pairs of unit and value, possibly with single sign at the end
    groups = [g for g in reversed(match.groups()) if g is not None]

    if len(groups) < 2:
        raise ValueError("Timedelta format is either empty or only a sign")
    
    total_seconds = Decimal()
    sign = 1

    if groups[-1] in '-+':
        if groups[-1] == '-':
            sign = -1

        groups.pop()

    for i in range(0, len(groups), 2):
        unit = groups[i].lower()[0]
        value = Decimal(groups[i + 1])

        if unit == 'd':
            total_seconds += value * 86400
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60
        else:
            total_seconds += value
    
    try:
        return dt.timedelta(seconds=float(total_seconds * sign))
    except Exception:
        raise ValueError("Number too small or big")
    

print(_parse_timedelta("10d"))