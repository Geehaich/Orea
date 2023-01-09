import orea_core as oc
from enum import Enum

"""we aim to provide basic filtering of entries based on common fields such as date, level or message but
because of the genericity offered by the YAML format, filtering entries based on content can't be fully covered by stock functions
we'd expose through our library. this filtering module is intended to be extended by custom functions adapted to what
you expect in your entries.

header filtering can be done by the rust backend if you pass functions with a signature of f( entry : LogEntry) -> bool to some functions in loglib.py,
filtering of optional fields requiring serialization will require a signature of f( Lm : LogManagerWrapper , entry : Logentry) -> bool
    """

class BoolOps(Enum):
    EQUAL = 0,
    GREATER = 1,
    GREATER_OR_EQUAL = 2,
    LESS = 3,
    LESS_OR_EQUAL = 4


"""below are basic function generators creating functions compatible with header filtering"""
def message_contains(substring = None) :
    def message_contains_f(entry : oc.LogEntry) -> bool :
        return substring in entry.message if substring else True
    return message_contains_f

def topic_contains(substring = None) :
    def topic_contains_f(entry : oc.LogEntry) -> bool :
        return substring in entry.topic if substring else True
    return topic_contains_f

def has_data() :
    def has_data_f(entry:oc.LogEntry) -> bool :
        return entry.dic_extension[1] > 0

    return has_data_f
def level_filter(level,op = BoolOps.LESS_OR_EQUAL) :

    def level_filter_f(entry : oc.LogEntry) -> bool :
        if op == BoolOps.EQUAL :
            return entry.level==level
        if op == BoolOps.LESS_OR_EQUAL :
            return entry.level<=level
        if op == BoolOps.LESS :
            return entry.level<level
        if op == BoolOps.GREATER :
            return entry.level>level
        if op == BoolOps.GREATER_OR_EQUAL :
            return entry.level>=level

    return level_filter_f

def default_header_func(level=6,op = BoolOps.LESS_OR_EQUAL,sub_message="",sub_topic="",data_presence=None) : #function accounting for all header fields

    def def_com_f(entry:oc.LogEntry) -> bool :
        total_bool = level_filter(level, op)(entry) and sub_topic in entry.topic and sub_message in entry.message
        if data_presence is not None :
            total_bool = total_bool and (entry.dic_extension[1] != 0) == data_presence
        return total_bool
    return def_com_f


""" below is an example of a function generator returning another function
 deserializing the data included in an entry, checking if a certain key is in the
result, and doing a check on the actual content (here, a ndarray).


def full_deser_example(trace_min) :

    def example_f(logmanwrap : LogManagerWrapper, entry : oc.LogEntry) -> bool :
        
        if entry.dic_extension[1] == 0 :
            return False
        d = logmanwrap.get_content(entry) #deserialize
        if d!= None and "MAT" in d.keys() :
            return numpy.trace(d["MAT"]) > 1
        else :
            return False
    return example_f
"""