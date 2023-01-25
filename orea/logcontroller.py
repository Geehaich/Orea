import rich
import sys
import os
from collections import deque

from .filtering import  default_header_func , BoolOps
from .loglib import LogManagerWrapper,LogLevels,LogEntry

LOG_EVENT_COLORS = ["bold bright_red blink","bold orange_red1","bold orange1","bold violet","bold blue","bold"]

class LogController :
    """controller class for interfacing. will store multiple LogManagerWrapper objects to track several files and handle events."""
    tribool = [True,False,None]
    def __init__(self,tracked_files : [str] , deque_size = 20):

        self.log_mans = {os.path.abspath(file): LogManagerWrapper(file,deque_max_len=deque_size) for file in tracked_files}
        self.is_paused = False
        self.is_fulltext = False

        self.max_msg_size = 50

        self.max_level = 6
        self.topic_substring = ""
        self.message_substring = ""
        self.data_presence_idx = 2
        self.filter = None
        self.update_filter() #header filter


        self.est_total_entries = 0 #sum of estimated number for each logmanagerWrapper
        self.est_total()
        for man in self.log_mans:
            self.log_mans[man].fill_queue(-1,self.filter)

        self.sorted_entries = []  # aggregation of logmanager deques, sorted by date
        self.contents_changed = False #used to tell the UI to collect entries before printing them
        self.collect_entries()

        self.new_entries = 0 #keep track of new entries added while paused

    def update_filter(self):

        self.filter =  default_header_func(self.max_level,BoolOps.LESS_OR_EQUAL,self.topic_substring,
                                      self.message_substring,LogController.tribool[self.data_presence_idx])
        self.contents_changed = True


        for mankey in self.log_mans :
            logman = self.log_mans[mankey]
            if len(logman.queue)!=0 :
                logman._logmanager.current_doc_extend = logman.queue[-1].total_extension
                logman._logmanager.move_doc(-1)
                logman._logmanager.move_doc(1)
                logman.queue.clear()
                logman.fill_queue(-1,self.filter)


    def collect_entries(self):

        aggregated_entries = []
        self.sorted_entries.clear()
        for logman in self.log_mans :
            for entry in self.log_mans[logman].queue :
                if entry not in aggregated_entries : #duplicates sometimes at ends of file
                    aggregated_entries.append(entry)
        if aggregated_entries :
            self.sorted_entries = sorted(aggregated_entries,reverse=True)
        else :
            self.sorted_entries = []

        self.contents_changed = False


    def scroll(self,amount):
        """scroll along entries by moving along every tracked file, checking the dates, and only moving the relevant logmanagers"""

        if amount == 0 :
            return

        if amount < 0 :
            for i in range(-amount):
                self._scroll_up_once()
        if amount > 0 :
            for i in range(amount):
                self._scroll_down_once()

        self.contents_changed = True

    def _scroll_down_once(self):

        for logman in self.log_mans:
            self.log_mans[logman].scroll(1,self.filter)
        entries = [self.log_mans[log].current_entry() for log in self.log_mans]
        dates = [e.date for e in entries if e is not None]
        if not dates:
            return
        mindate = min(dates)
        for e in entries:
            if e is not None and e.date != mindate:
                e.log_man_ref.scroll(-1,self.filter)

    def _scroll_up_once(self):

        not_beg_lmans = [self.log_mans[lman] for lman in self.log_mans if self.log_mans[lman]._logmanager.current_doc_extend[0]!=0] #need to filter entries at beginning
        for logman in not_beg_lmans :
            logman.scroll(-1,self.filter)
        entries = [logman.current_entry() for logman in not_beg_lmans]
        dates = [e.date for e in entries if e is not None]
        if not dates:
            return
        maxdate = max(dates)
        for e in entries :
            if e is not None and e.date != maxdate :
                e.log_man_ref.scroll(1,self.filter)

    def jump_first(self):
        for logman in self.log_mans:
            self.log_mans[logman].jump_first()
            self.log_mans[logman].fill_queue(1,self.filter)
        self.contents_changed = True

    def jump_last(self):
        for logman in self.log_mans:
            self.log_mans[logman].jump_last()
            self.log_mans[logman].fill_queue(-1,self.filter)
        self.contents_changed = True

    def search_date(self,date):
        for logman in self.log_mans:
            self.log_mans[logman].search_date(date)
            self.log_mans[logman].fill_queue(-1,self.filter)
        self.contents_changed = True


    def print_plaintext(self,fpath):
    
        fpath = os.path.abspath(fpath)
        self.log_mans[fpath].jump_last()
        entry = self.log_mans[fpath].current_entry()
        
        if entry is not None and self.filter(entry) ==True  :
            if self.last_entry_printed is None or self.last_entry_printed != entry:
                print(entry)
                self.last_entry_printed = entry

    def est_total(self):
        """randomly sample a few entries per logmanager for size, compare to file length and estimate a number of entries for all tracked files"""
        total = 0
        for logman in self.log_mans :
            total +=  self.log_mans[logman]._logmanager.entry_size_estimate()
        self.est_total_entries = total
