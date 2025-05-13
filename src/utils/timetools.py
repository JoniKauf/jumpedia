import datetime
from decimal import Decimal
import re

# Regex and function created by Joni. If you use it, mention me if u wanna be cool af :)
_TIMEDELTA_PARSE_PATTERN = re.compile(r'''
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
        (h|hrs?|hours?)       # [Group 5: 'h', 'hr', 'hrs', 'hour' or 'hours']
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
            (?:[.,][0-9]*)?       # followed by optional: '.' or ',' followed by any digits 0 to ∞ times
        )                     # ]
        \s*                   # Whitespace 0 to ∞ times
        (s|secs?|seconds?)    # [Group 9: 's', 'sec', 'secs', 'second' or 'seconds']
    )?                    # End group, its insides must either fully match or not exist at all
''', re.VERBOSE | re.IGNORECASE)


def parse_timedelta(s: str) -> datetime.timedelta:
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
        unit = groups[i][0].lower()
        value = Decimal(groups[i + 1].replace('.', ',', 1))

        if unit == 'd':
            total_seconds += value * 86400
        elif unit == 'h':
            total_seconds += value * 3600
        elif unit == 'm':
            total_seconds += value * 60
        else:
            total_seconds += value
    
    try:
        return datetime.timedelta(seconds=float(total_seconds * sign))
    except Exception:
        raise ValueError("Number too small or big")
    

def unparse_timedelta(obj: datetime.timedelta) -> str:
    if obj.total_seconds() < 0:
        parts: list[str] = ["-"]
    else:
        parts: list[str] = []
    
    mins, seconds = divmod(obj.seconds, 60)
    hours, mins = divmod(mins, 60)

    if obj.microseconds:
        seconds += (obj.microseconds / 1_000_000)

    if obj.days: 
        parts.append(f"{abs(obj.days)}d")
    if hours: 
        parts.append(f"{abs(hours)}h")
    if mins: 
        parts.append(f"{abs(mins)}m")
    if seconds:
        parts.append(f"{abs(seconds)}s")
        
    return ''.join(parts)