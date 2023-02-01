import rich
import sys
import os
from collections import deque

from .filtering import  default_header_func , BoolOps
from .loglib import LogManagerWrapper,LogLevels,LogEntry

from datetime import timedelta

LOG_EVENT_COLORS = ["bold bright_red blink","bold orange_red1","bold orange1","bold violet","bold blue","bold"]

class LogController :
    """controller class for interfacing. will store multiple LogManagerWrapper objects to track several files and handle events."""
    tribool = [True,False,None]
    def __init__(self,tracked_files : [str] , deque_size = 20):
        """ctor creating LogManagerWrapper objects linked to each file, regrouping them in a dict, and setting default
        filter parameters.

        :param [str] tracked_files : a list of paths pointing to .yaml file paths. The files will be created if they don't exist but their folder does.
        :param int deque_size : size of each LogManagerWrapper's entries deque. defaults to 20
        :ivar log_mans: dict regrouping individual logmanagers
        :ivar is_paused : paused status
        :ivar topic_substring : substring to search in topics for filtering entries
        :ivar message_substring : substring to search in topics for filtering entries
        :ivar filter : entry filtering function
        :ivar search_timeout : timedelta object used as search timeout on all tracked wrappers
        :ivar est_total_entries : vague estimate of the total amount of entries in all files
        :ivar sorted_entries : a list used to aggregate entries and sort them by date for display
        :ivar contents_changed : flag indicating sorted_entries need to be rebuilt
        """

        self.log_mans = {os.path.abspath(file): LogManagerWrapper(file,deque_max_len=deque_size) for file in tracked_files}
        self.is_paused = False

        self.max_level = 5
        self.topic_substring = ""
        self.message_substring = ""
        self.data_presence_idx = 2
        self.filter = None
        self.update_filter() #header filter

        self.search_timeout = timedelta(seconds = 180)
        self.set_timeout(self.search_timeout)


        self.est_total_entries = 0 #sum of estimated number for each logmanagerWrapper
        self.est_total()
        for man in self.log_mans:
            self.log_mans[man].fill_queue(-1,self.filter)

        self.sorted_entries = []  # aggregation of logmanager deques, sorted by date
        self.contents_changed = False #used to tell the UI to collect entries before printing them
        self.collect_entries()


    def update_filter(self):
        """create a new header filtering function using parameters currently stored in the controller, raises content flag"""
        self.filter =  default_header_func(self.max_level,BoolOps.LESS_OR_EQUAL,self.topic_substring,
                                      self.message_substring,LogController.tribool[self.data_presence_idx])
        self.contents_changed = True


        for mankey in self.log_mans :


            logman = self.log_mans[mankey]
            logman.nothing_up_close = False #reset search timeouts
            logman.nothing_down_close = False
            if len(logman.queue)!=0 :
                logman._logmanager.byte_jump(logman.queue[-1].total_extension[0] + logman.queue[-1].total_extension[1]//2)
                logman.queue.clear()
                logman.fill_queue(-1,self.filter)


    def collect_entries(self):
        """gather every currently stored entry into a list sorted by date."""
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


    def scroll(self,amount,inf_scroll=False):
        """scroll along entries by moving along every tracked file, checking the dates, and only moving the relevant logmanagers

        :param int amount : the amount of times we'll attempt to scroll. goes to earlier entries if <0, later otherwise
        :param bool inf_scroll : whether to ignore search timeout. used by UI live mode while going down the file."""

        if amount == 0 :
            return

        if amount < 0 :
            for i in range(-amount):
                self._scroll_up_once(inf_scroll)
        if amount > 0 :
            for i in range(amount):
                self._scroll_down_once(inf_scroll)

        self.contents_changed = True

    def _scroll_down_once(self,inf_scroll):
        """scroll every logmanager once, check the earliest new entry, and scroll the logmanagers not containing it back up

        :param bool inf_scroll : ignore search timeout"""

        moved_log_mans = {}
        for logman in self.log_mans:
            if  not self.log_mans[logman].isateof() :
                r = self.log_mans[logman].scroll(1,self.filter,inf_scroll=inf_scroll)
                if r is not None and r !=-1:
                    moved_log_mans[self.log_mans[logman]] = r
        entries = [logman.current_entry() for logman in moved_log_mans ]
        dates = [e.date for e in entries if e is not None]
        if not dates:
            return
        mindate = min(dates)
        for e in entries:
            if e is not None and e.date != mindate:
                e.log_man_ref.scroll(-1,self.filter)
                if e.log_man_ref.nothing_down_close :
                    e.log_man_ref.search_date(mindate)
                    e.log_man_ref.nothing_down_close = False


    def _scroll_up_once(self,inf_scroll):
        """same as scroll_down_once but in the other direction"""
        moved_log_mans = {}
        for logman in self.log_mans :
            if len(self.log_mans[logman].queue)!=0 and self.log_mans[logman].queue[0].total_extension[0]!=0 :
                r = self.log_mans[logman].scroll(-1,self.filter,inf_scroll=inf_scroll)
                if r is not None :
                    moved_log_mans[self.log_mans[logman]] = r
        entries = [logman.current_entry() for logman in moved_log_mans]
        dates = [e.date for e in entries if e is not None]
        if not dates:
            return
        maxdate = max(dates)
        for e in entries :
            if e is not None and e.date != maxdate and moved_log_mans[self.log_mans[logman]]!=-1 :
                e.log_man_ref.scroll(1,self.filter)
                if e.log_man_ref.nothing_up_close :
                    e.log_man_ref.search_date(maxdate)
                    e.log_man_ref.nothing_up_close = False


    def jump_first(self):
        """jump to the beginning of every tracked file and raise the contents_changed flag to have the entry list rebuilt later"""
        total = 0
        for logman in self.log_mans:
            total += self.log_mans[logman].jump_first(header_cond_function=self.filter,refill=True) #jump first returns 0 if we were already at beginning
        if total !=0 :
            self.contents_changed = True


    def jump_last(self):
        """jump to EoF for every tracked file"""
        total = 0
        for logman in self.log_mans:
            total += self.log_mans[logman].jump_last(header_cond_function=self.filter,refill=True)  # jump first returns 0 if we were already at beginning
        if total !=0 :
            self.contents_changed = True
        self.contents_changed = True
    def search_date(self,date,refill=True):
        """set the cursor for every LogmanagerWrapper to the first entry with a date <= the date parameter.

        :param date|str date : a datetime or ISO date string representing the target date.
        :param bool refill : refill every tracked deque"""

        for logman in self.log_mans:
            self.log_mans[logman].search_date(date)
            if refill :
                self.log_mans[logman].fill_queue(-1,self.filter)
        self.contents_changed = True

    def set_timeout(self,timeout):
        """set time search intervals for each logmanager, reset search flags"""
        self.search_timeout = timeout
        for logman in self.log_mans:
            self.log_mans[logman].search_timeout = timeout
        self.contents_changed = True


    def is_search_zone_limit(self):
        """check if all LogManagers have timed out for display"""
        limit_down = True
        limit_up = True
        for log_man in self.log_mans :
            limit_up &= self.log_mans[log_man].nothing_up_close
            limit_down &= self.log_mans[log_man].nothing_down_close
        return limit_up,limit_down

    def mean_position(self):
        """estimate of position of cursos in entries using the mean cursor position in files"""
        mean_p = 0
        i = 0
        for log_man in self.log_mans :
            mean_p += self.log_mans[log_man].position_percent()
            i +=1
        return round(mean_p/i*100,2)


    def all_eof(self):
        """check if all logmanagers are at EoF to stop iterating in live mode"""
        for man in self.log_mans:
            if not self.log_mans[man].isateof():
                return False
        return True

    def est_total(self):
        """randomly sample a few entries per logmanager for size, compare to file length and estimate a number of entries for all tracked files"""
        total = 0
        for logman in self.log_mans :
            total +=  self.log_mans[logman]._logmanager.entry_size_estimate()
        self.est_total_entries = total
