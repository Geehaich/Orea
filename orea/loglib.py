from datetime import datetime
from enum import Enum

import yaml
import os
import psutil
from collections import deque,OrderedDict
from threading import Lock

from . import orea_core


class LogLevels(Enum) : #classic log levels for most applications
    FATAL = 0
    ERROR = 1
    WARN = 2
    INFO = 3
    DEBUG = 4
    TRACE = 5



class LogManagerWrapper :
    """wrapper on LogManager rust struct providing convenience functions and type conversions to Rust compatible types."""
    def __init__(self,fpath, deque_max_len = 25):

        fpath = os.path.abspath(fpath)
        if not os.path.exists(fpath):
            open(fpath, 'w+').close()
        self._logmanager = orea_core.LogManager(fpath)
        self.file = open(fpath, 'a', encoding="utf-8")
        self.path = self._logmanager.file_name

        self.queue = deque(maxlen=deque_max_len)
        self.cursor_date = None #will stay None if empty file
        self.write_lock = Lock()
        self.read_lock = Lock() #deserialization

        last_entry = self.current_entry()
        if last_entry is not None :
            self.queue.append(last_entry)
            self.cursor_date = datetime.fromisoformat(last_entry.date)


    #slice_up/slice_down c
    def _scroll_up(self,n, header_cond_function = None, content_cond_function = None) :
        """collect documents from the current one going up in the bound file (previous entries) and appends them in the deque, optionally filtering them using a header and content
    #filtering function. moves the cursor up the file"""

        if len(self.queue) !=0 : #move current doc to oldest in queue
            self._logmanager.current_doc_extend = self.queue[0].total_extension
        interval = [LogEntry(self,e) for e in self._logmanager.slice_conditional(n,0,header_cond_function)]
        if content_cond_function is not None :
            interval = [e for e in interval if content_cond_function(e)==True ]
        self.queue.extendleft(interval)
        if len(self.queue) !=0 : #move current doc to oldest in queue
            self._logmanager.current_doc_extend = self.queue[0].total_extension

    def _scroll_down(self, n, header_cond_function = None, content_cond_function = None) :
        """same as slice_up in opposite direction"""

        if len(self.queue) !=0:
            self._logmanager.current_doc_extend = self.queue[-1].total_extension
        self._logmanager.search_date(self.queue[-1].date)
        interval = [LogEntry(self,e) for e in self._logmanager.slice_conditional(0,n, header_cond_function)][1:]
        if content_cond_function is not None:
            interval = [e for e in interval if content_cond_function(e) == True]
        self.queue.extend(interval)
        if len(self.queue) !=0:
            self._logmanager.current_doc_extend = self.queue[-1].total_extension

    def scroll(self, n, header_cond_function = None, content_cond_function = None) :

        if n == 0:
            return
        elif n > 0 :
            self._scroll_down(n, header_cond_function, content_cond_function)
        else :
            self._scroll_up(-n, header_cond_function, content_cond_function)


    def crawl_until(self,direction : int,header_cond_function = None, content_cond_function = None):
        """moves along the file until an entry meets search criteria, stores it in the queue"""

        if header_cond_function is None and content_cond_function is None :
            raise ValueError("both filtering functions set to None.")

        increment = -1 if direction <0 else 1
        entry = None
        while True :

            self.move(increment)
            entry = self.current_entry()

            if entry is None : #either end of file, return None as stop condition for filling function
                return None


            stop_condition = True
            if content_cond_function is not None:
                stop_condition = stop_condition and content_cond_function(entry)
            if header_cond_function is not None :
                stop_condition = stop_condition and header_cond_function(entry)

            if stop_condition :
                break
        if increment  == -1 and entry is not None:
            self.queue.appendleft(entry)
        if increment == 1 and entry is not None:
            self.queue.append(entry)
        return 0 #return something other than None

    def fill_queue(self,direction = -1, header_cond_function = None, content_cond_function = None):
        """fill entry queue in either direction using optional filtering functions"""
        increment = -1 if direction < 0 else 1
        space_left = self.queue.maxlen -1 #keep the starting entry somewhere in queue

        if header_cond_function is None and content_cond_function is None :
            if direction <0 :
                self.queue.clear()
                self._scroll_up(space_left)
            else :
                self.queue.clear()
                self._scroll_down(space_left)

        else :
            while space_left !=0 :

                res = self.crawl_until(direction,header_cond_function,content_cond_function)
                if res is None :
                    return
                else :
                    space_left -= 1






    def search_date(self,date):
        """moves to the entry with the specified date or the first one older than that. date should be a datetime object or an ISO date string """
        if isinstance(date,datetime):
            self._logmanager.search_date(str(date))
        else :
            self._logmanager.search_date(date)

    def move(self,amount : int) :
        """move along documents, direction specified by sign of amount.
        moving past the last or first document places the cursor back on the extremal document and return None, so does
        calling move on an empty file.
        """

        if amount == 0 :
            return

        self._logmanager.move_doc(amount)
        if self.current_entry() is not None :
            self.cursor_date = datetime.fromisoformat(self.current_entry().date)
        else :
            if self._logmanager.file_byte_len()>0 and amount > 0 :
                self.jump_last()
            return None

    def get_content(self,entry : orea_core.LogEntryCore) -> dict :
        return yaml.load(self._logmanager.get_content(entry),yaml.Loader)

    def date_interval(self,d1 :datetime.date ,d2 : datetime.date, cond_func = None):
        """returns all entries between two date objects (or any object for which __repr__ returns an ISO formated date string,
        which also optionally meet a user defined criterium using a function of signature"""

        all_slice = self._logmanager.date_interval(str(d1),str(d2),None)
        if cond_func is None :
            return all_slice
        else :
            return [entry for entry in all_slice if cond_func(self,entry)==True]

    def current_entry(self):
        core_ent = self._logmanager.current_entry()
        return LogEntry(self,core_ent) if core_ent is not None else None

    def current_core_entry(self):
        return self._logmanager.current_entry()


    def jump_first(self):
        self._logmanager.jump_first()

    def jump_last(self):
        self._logmanager.jump_last()

    def new_entry(self,message ="", level=0, topic = "", serialize_dict = None) :
        """add new entry to the file the manager object is connected to. uses lock files for eventual multiprocess access"""

        date = datetime.now()
        _level = level.value if isinstance(level, Enum) else level



        with self.write_lock:
            if not serialize_dict:  # print message directly without yaml dumping, saves a bit of performance
                self.file.seek(os.SEEK_END)
                self.file.write(
                    "date: {}\nlevel: {}\ntopic: {}\nmessage: {}\n---\n".format(date, _level, topic, message))
                self.file.flush()
                return

            content_dict = {"date":date,"level":_level,"topic":topic,"message":message}
            content_dict.update(serialize_dict)
            content_str = yaml.dump(content_dict, sort_keys=False, allow_unicode=True)+'---\n'
            self.file.write(content_str)
            self.file.flush()


class LogEntry :
    """wrapper around LogEntryCore to allow more ergonomic deserialization by keeping references to LogManagerWrapper objects"""

    def __init__(self,log_man:LogManagerWrapper,entry : orea_core.LogEntryCore):
        self.log_man_ref = log_man
        self.entry = entry

    def __getattr__(self, item):
        if item in ["date","level","message","topic","dic_extension","total_extension"]:
            return getattr(self.entry,item)
        elif item == "log_man_ref" :
            return self.log_man_ref
        elif item == "entry" :
            return self.entry
        else :
            raise KeyError(f" 'Logentry' object has no attribute {item}")

    def __repr__(self):
        return self.entry.__repr__()
    def deserialize(self):
        """use deserialization function of LogManager for ergonomics"""
        if self.dic_extension[1] == 0:
            return None
        else:
            try :
                self.log_man_ref.read_lock.acquire()
                core_ent = self.entry
                dic =self.log_man_ref.get_content(core_ent)
                return dic
            finally :
                self.log_man_ref.read_lock.release()

    def __lt__(self, other):
        return self.date<other.date if other.date is not None else False
    def __gt__(self, other):
        return self.date>other.date if other.date is not None else True