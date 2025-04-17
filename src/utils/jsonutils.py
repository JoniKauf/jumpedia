import json
from typing import Any
from discordtools import feedbackerrors as fbe

HARD_MAX_LENGTH = 2**20

# From https://stackoverflow.com/a/30928645/20895654
def json_depth(o: Any) -> int:
    if isinstance(o, dict) and o:
        return 1 + max(json_depth(o[a]) for a in o)
    if isinstance(o, list) and o:
        return 1 + max(json_depth(a) for a in o)
    return 0

def json_loads_safe(s: str, max_depth: int = -1, max_length: int = -1, **kwargs: Any) -> Any:
    length = len(s)

    max_length = max_length if max_length >= 0 else HARD_MAX_LENGTH

    if length > max_length:
        raise fbe.TemporaryFeedbackError(length, max_length)
    
    try:
        result: Any = json.loads(s, **kwargs)
    except json.JSONDecodeError as e:
        raise fbe.TemporaryFeedbackError()
    except RecursionError:
        raise fbe.TemporaryFeedbackError()
    
    if max_depth >= 0 and (depth := json_depth(result)) > max_depth:
        raise fbe.TemporaryFeedbackError(depth)

    return result