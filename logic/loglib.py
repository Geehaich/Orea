from datetime import datetime
from enum import Enum

import yaml
import orea_core
import os
import psutil
from collections import deque,OrderedDict


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

        if os.path.exists(fpath) == False :
            open(fpath,"w").close()
        self._logmanager = orea_core.LogManager(fpath)

        self.queue = deque(maxlen=deque_max_len)

        last_entry = self._logmanager.current_entry() #none if empty file
        self.cursor_date = datetime.fromisoformat(last_entry.date) if last_entry is not None else None

    #slice_up/slice_down c
    def slice_up(self,n, header_cond_function = None, content_cond_function = None) :
        """collect documents from the current one going up in the bound file (previous entries) and appends them in the deque, optionally filtering them using a header and content
    #filtering function. moves the cursor up the file"""

        interval = self._logmanager.slice_conditional(n,0,header_cond_function)
        if content_cond_function is not None :
            interval = [entry for entry in interval if content_cond_function(self,entry)==True]
        self.queue.extendleft(interval)
        if len(self.queue)!=0:
            self._logmanager.current_doc_extend = self.queue[-1].total_extension
    def slice_down(self, n, header_cond_function = None, content_cond_function = None) :
        """same as slice_up in opposite directoin"""

        interval = self._logmanager.slice_conditional(0,n,header_cond_function)
        if content_cond_function is not None :
            interval = [entry for entry in interval if content_cond_function(self,entry)==True]
        self.queue.extend(interval)
        if len(self.queue)!=0:
            self._logmanager.current_doc_extend = self.queue[0].total_extension

    def search_date(self,date):
        """returns the entry with the specified date or the first one older than that. date should be a datetime object or an ISO date string """
        if isinstance(date,datetime):
            self._logmanager.search_date(str(date))
        else :
            self._logmanager.search_date(date)

    def move(self,amount : int) :
        """move along documents, direction specified by sign of amount"""
        self._logmanager.move_doc(amount)
        if self._logmanager.current_entry() is not None :
            self.cursor_date = datetime.fromisoformat(self._logmanager.current_entry().date)
        else :
            if self._logmanager.file_byte_len()>0 and amount > 0 :
                self.jump_last()

    def get_dict_fields(self,entry) :
        """deserializes optional dict_fields, returns a python dict"""
        if entry.dic_extension[1]==0 : #case no optionals
            return None
        else :
            entry_string = self._logmanager.get_content(entry)
            return yaml.load(entry_string,yaml.Loader)

    def date_interval(self,d1 :datetime.date ,d2 : datetime.date, cond_func = None):
        """returns all entries between two date objects (or any object for which __repr__ returns an ISO formated date string,
        which also optionally meet a user defined criterium using a function of signature"""

        all_slice = self._logmanager.date_interval(str(d1),str(d2),None)
        if cond_func is None :
            return all_slice
        else :
            return [entry for entry in all_slice if cond_func(self,entry)==True]

    def current_entry(self):
        return self._logmanager.current_entry()

    def full_current_entry(self):
        entry = self._logmanager.current_entry()
        if entry.dic_extension[1] == 0 :
            return entry,None
        else :
            D = yaml.load(self._logmanager.get_content(entry),yaml.Loader)
            return entry,D

    def jump_first(self):
        self._logmanager.jump_first()

    def jump_last(self):
        self._logmanager.jump_last()

    def check_lock(self) :
        lock_filename = self._logmanager.file_name + '.lock'
        if os.path.exists(lock_filename) == False :
            return False
        else :
            f_lock =  open(lock_filename,'r')
            pid = int(f_lock.readline())
            if psutil.pid_exists(pid) :
                return True
            else :
                f_lock.close()
                os.remove(lock_filename)
                return False
    def new_entry(self,message ="", level=0, process = "", serialize_dict = None) :
        """add new entry to the file the manager object is connected to. uses lock files for eventual multiprocess access"""
        while self.check_lock() == True :
            pass

        lock_filename = self._logmanager.file_name + '.lock'
        with open(lock_filename,"w") as f_lock :
            f_lock.write(str(os.getpid()))

        date = datetime.now()
        _level = level.value if isinstance(level,Enum) else level
        content_dict = dict(OrderedDict({"date":date,"level":_level,"topic":process,"message":message}))
        if serialize_dict :
            content_dict.update(serialize_dict)
        with open(self._logmanager.file_name,'a',encoding="utf-8") as dump_stream :
            yaml.dump(content_dict,dump_stream,sort_keys=False,allow_unicode=True)
            dump_stream.write("---\n")

        os.remove(lock_filename)

