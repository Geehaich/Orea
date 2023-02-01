from datetime import datetime,timedelta
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

DEFAULT_CRAWL_TIMEOUT = timedelta(seconds = 180)

class LogManagerWrapper :
    """wrapper on LogManager rust struct providing convenience functions and type conversions to Rust compatible types."""
    def __init__(self,fpath, deque_max_len = 20):
        """ctor, initializes a LogManager object and a deque for entries.

        :param str fpath : tracked .yaml file
        :param int deque_max_len : size of the entry deque. default 20"""
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

        self.pause= False

        last_entry = self.current_entry()
        if last_entry is not None :
            self.queue.append(last_entry)
            self.cursor_date = datetime.fromisoformat(last_entry.date)


        self.search_timeout = DEFAULT_CRAWL_TIMEOUT


    #slice_up/slice_down c
    def _scroll_up(self,n, header_cond_function = None, content_cond_function = None,inf_scroll = False) :
        """collect documents from the current one going up in the bound file (previous entries) and appends them in the deque, optionally filtering them using a header and content
    #filtering function. moves the cursor up the file.

    :param func header_cond_function : filtering function with an access to every LogEntryField except the deserialized content
    :param func content_cond_function : filtering function also accounting for deserialized content
    :param bool inf_scroll : ignore search timeout. default : False"""
        result = 0
        if len(self.queue)!=0 and self.queue[0] is not None:
            self._logmanager.byte_jump( self.queue[0].total_extension[0] + self.queue[0].total_extension[1]//2) #set cursor position to earliest entry
        for i in range(n) :
            result = self.crawl_until(-1,header_cond_function,content_cond_function,inf_scroll)
        return result

    def _scroll_down(self, n, header_cond_function = None, content_cond_function = None,inf_scroll = False) :
        """same as scroll_up in opposite direction"""
        result = 0
        if len(self.queue)!=0 and self.queue[-1] is not None:
            self._logmanager.byte_jump(self.queue[-1].total_extension[0] + self.queue[-1].total_extension[1] // 2)  # set cursor position to latest entry
        for i in range(n):
            result = self.crawl_until(1, header_cond_function, content_cond_function,inf_scroll)
        return result
    def scroll(self, n, header_cond_function = None, content_cond_function = None , inf_scroll = False) :
        """calls scroll_up and scroll_down multiple time to move along the document.

        :param int n : amount of valid entries we go over."""
        if n == 0:
            return None
        elif n > 0 :
            counter = 0
            scroll_res = 0
            while counter < n and scroll_res is not None :
                counter+=1
                scroll_res = self._scroll_down(1, header_cond_function, content_cond_function,inf_scroll)
            if scroll_res is None :
                return None
        else :
            counter = 0
            scroll_res = 0
            while counter < -n and scroll_res is not None :
                counter+=1
                scroll_res = self._scroll_up(1, header_cond_function, content_cond_function,inf_scroll)
            if scroll_res is None :
                return None


    def crawl_until(self,direction : int, header_cond_function = None, content_cond_function = None, inf_scroll = False):
        """moves along the file until an entry meets search criteria, stores it in the queue"""

        if header_cond_function is None and content_cond_function is None :
            if direction < 0 :
                self.move(-1)
                ent = self.current_entry()
                if ent is not None :
                    if len(self.queue)!=0 and self.queue[0] is not None :

                        if not ent.total_extension[0]==self.queue[0].total_extension[0]==0 :
                            self.queue.appendleft(ent)
                else :
                    return None
            elif direction > 0 :
                self.move(1)
                ent = self.current_entry()
                if ent is not None:
                    if len(self.queue) != 0 and  self.queue[-1] is not None :
                        if not ent.total_extension[0]==self.queue[-1].total_extension[0]:
                            self.queue.append(ent)
                else :
                    return None
            return 0

        increment = -1 if direction <0 else 1

        if (inf_scroll == False) and (self.nothing_down_close and increment == 1) or (self.nothing_up_close and increment ==-1) :
            return

        entry = self.current_entry()
        cur_date = self.current_entry().date_obj()
        moved = 0
        while True :

            self.move(increment)
            moved +=1
            entry = self.current_entry()

            if entry is None : #either end of file, return None as stop condition for filling function
                return None


            stop_condition = True
            if content_cond_function is not None:
                stop_condition = stop_condition and content_cond_function(entry)
            if header_cond_function is not None :
                stop_condition = stop_condition and header_cond_function(entry)

            if inf_scroll == False and abs(entry.date_obj() - cur_date) > self.search_timeout :
                if increment == 1:
                    self.nothing_down_close = True
                else :
                    self.nothing_up_close = True
                return -1


            extremal_condition = entry.total_extension[0]==0 or self.isateof()
                     #check if document is at either end of file

            if stop_condition : #condition met, add to queue
                break

            if extremal_condition : #end of file reached and condition not met, leave
                return None

        if increment  == -1 and entry is not None:
            if len(self.queue)==0 or (len(self.queue)!=0 and entry.total_extension[0]!=self.queue[0].total_extension[0]):
                self.queue.appendleft(entry)
                self.nothing_down_close = False #allows going back to previous entries
        if increment == 1 and entry is not None:
            if len(self.queue)==0 or entry.total_extension[0]!=self.queue[-1].total_extension[0]:
                self.queue.append(entry)
                self.nothing_up_close = False
        return moved

    def fill_queue(self,direction = -1, header_cond_function = None, content_cond_function = None):
        """fill entry queue in either direction using optional filtering functions"""
        increment = -1 if direction < 0 else 1
        space_left = self.queue.maxlen -1 #keep the starting entry somewhere in queue

        if header_cond_function is None and content_cond_function is None :
            if direction <0 :
                self.queue.clear()
                self.queue.append(self.current_entry())
                self._scroll_up(space_left)
            else :
                self.queue.clear()
                self.queue.append(self.current_entry())
                self._scroll_down(space_left)

        else :

            self.queue.clear()
            cur_ent = self.current_entry()
            if cur_ent is not None :
                current_fits = True
                if header_cond_function is not None :
                    current_fits = current_fits and header_cond_function(cur_ent.entry)
                if content_cond_function is not None :
                    current_fits = current_fits and content_cond_function(cur_ent)
                if current_fits :
                    self.queue.append(cur_ent)

            while space_left !=0 :

                res = self.crawl_until(direction,header_cond_function,content_cond_function)
                if res is None :
                    return
                else :
                    space_left -= 1


    def position_percent(self):
        """returns the percentage of the current byte position to the total file length. """
        return self._logmanager.current_doc_extend[0]/self._logmanager.file_byte_len()

    def isateof(self):
        """compare current doc extension to file size to check if the cursor is at the end of the file"""
        return self._logmanager.file_byte_len() - (self._logmanager.current_doc_extend[0]+self._logmanager.current_doc_extend[1]) < 10




    def search_date(self,date):
        """moves to the entry with the specified date or the first one older than that. date should be a datetime object or an ISO date string """

        self.nothing_up_close = False
        self.nothing_down_close = False

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
            return None

        self._logmanager.move_doc(amount)
        if self.current_entry() is not None :
            self.cursor_date = datetime.fromisoformat(self.current_entry().date)
        else : #case of empty file
            if self._logmanager.file_byte_len()>0 and amount > 0 :
                self.jump_last(refill=False)
            return None

    def get_content(self,entry : orea_core.LogEntryCore) -> dict :
        """get optional content from a LogEntryObject as a dict. You should favor using the deserialize method of a LogEntry to get contents, it will call this one on itself."""
        text =self._logmanager.get_content(entry).replace("---\n",'')
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
        """return the LogEntry the file cursor is currently pointing to"""
        core_ent = self._logmanager.current_entry()
        return LogEntry(self,core_ent) if core_ent is not None else None

    def current_core_entry(self):
        """return the LogEntryCore the file cursor is currently pointing to"""
        return self._logmanager.current_entry()


    def jump_first(self,refill = True,header_cond_function = None, content_cond_function = None):
        """move to beginning of file.
        :param bool refill : if True, reset the entry deque
        :param header_cond_function : header filter function used if refilling
        :param content_cond_function :content filter"""
        self.nothing_up_close = False
        self.nothing_down_close = False

        self._logmanager.jump_first()
        first_ent = self.current_entry()
        if len(self.queue)!=0 and first_ent == self.queue[0]:
            return
        else :
            if refill :
                self.fill_queue(1,header_cond_function,content_cond_function)
            return len(self.queue)
        return 0


    def jump_last(self,refill=True,header_cond_function = None, content_cond_function = None):
        """Move to EoF, optional refill of deque"""

        self.nothing_up_close = False
        self.nothing_down_close = False

        self._logmanager.jump_last()
        last_ent = self.current_entry()
        if len(self.queue)!=0 and last_ent == self.queue[-1]:
            return
        else:
            if refill:
                self.fill_queue(-1, header_cond_function, content_cond_function)
            return len(self.queue)
        return 0

    def new_entry(self,message ="", level=0, topic = "", serialize_dict = None) :
        """add new entry to the file the manager object is connected to.

        :param str message : entry message
        :param int level : entry log level. should be between 0-99
        :param str topic : entry topic, used for filtering later
        :param serialize_dict : oprional dictionary serialized as YAML and appended to the file along with the rest"""

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
    """
    wrapper around LogEntryCore to allow more ergonomic deserialization by keeping references to LogManagerWrapper objects

    :ivar log_man_ref: reference to the LogManagerWrapper which created the file
    :ivar entry: LogEntryCore defined in the rust API containing header info and byte extension
    :ivar extra: stores extra content after the function was called to avoid multiple costly deserializations"""

    def __init__(self,log_man:LogManagerWrapper,entry : orea_core.LogEntryCore):
        self.log_man_ref = log_man
        self.entry = entry
        self.extra = {} #store content in case of deserialization to avoid loading it several times

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
        """use deserialization function of LogManager. stores the result in the object to avoid loading it several times"""
        if self.dic_extension[1] == 0:
            return None
        else:

            if self.extra :
                return self.extra
            else :

                try :
                    self.log_man_ref.read_lock.acquire()
                    core_ent = self.entry
                    self.extra =self.log_man_ref.get_content(core_ent)
                    return self.extra
                finally :
                    self.log_man_ref.read_lock.release()
    def date_obj(self):
        """return date as a datetime object to allow for actual date arithmetics instead of boolean comparison the ISO string format allows"""
        return datetime.fromisoformat(self.entry.date)

    def __lt__(self, other):
        return self.date<other.date if other is not None else False
    def __gt__(self, other):
        return self.date>other.date if other is not None else True