import yaml
import orea_core as oc
from enum import Enum

"""we aim to provide basic filtering of entries based on common fields such as date, level or message but
because of the genericity offered by the YAML format, filtering entries based on content can't be fully covered by stock functions
we'd expose through our library. this filtering module is intended to be extended by custom functions adapted to what
you expect in your entries.

functions must have LogEntry objects as arguments and return booleans to be compatible with our slicing functions.

e.g , keep all entries containing an invertible array in their optional fields:
    
    
    """


class BoolOps(Enum):
    EQUAL = 0,
    GREATER = 1,
    GREATER_OR_EQUAL = 2,
    LESS = 3,
    LESS_OR_EQUAL = 4
