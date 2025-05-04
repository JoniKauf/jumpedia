import json
from typing import Any, Final
from discordtools import feedbackerrors as fbe

DEFAULT_MAX_LENGTH: Final[int] = 2**20
ENCODING: Final[str] = 'utf-8'

# From https://stackoverflow.com/a/30928645/20895654
def json_depth(o: Any) -> int:
    if isinstance(o, dict) and o:
        return 1 + max(json_depth(o[a]) for a in o)
    if isinstance(o, list) and o:
        return 1 + max(json_depth(a) for a in o)
    return 0

def json_loads_safe(s: str, max_depth: int = -1, max_length: int = DEFAULT_MAX_LENGTH, **kwargs: Any) -> Any:
    length = len(s)

    if length > max_length:
        raise fbe.TemporaryFeedbackError(length, max_length)
    
    try:
        result: Any = json.loads(s, **kwargs)
    except (json.JSONDecodeError, TypeError) as e:
        raise fbe.TemporaryFeedbackError()
    except RecursionError:
        raise fbe.TemporaryFeedbackError()
    except Exception:
        raise fbe.TemporaryFeedbackError()
    
    if max_depth >= 0 and (depth := json_depth(result)) > max_depth:
        raise fbe.TemporaryFeedbackError(depth)

    return result