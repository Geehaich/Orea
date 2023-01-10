import rich
import sys
import os
from collections import deque

from . import orea_core
from .filtering import  default_header_func , BoolOps
from .loglib import LogManagerWrapper,LogLevels

LOG_EVENT_COLORS = ["bold bright_red blink","bold orange_red1","bold orange1","bold violet","bold blue","bold"]

class LogController :
    """controller class for interfacing. will store multiple LogManagerWrapper objects to track several files and handle events."""
    tribool = [True,False,None]
    def __init__(self,tracked_files : [str] , cursed = None):

        self.log_mans = {os.path.abspath(file): LogManagerWrapper(file) for file in tracked_files}
        self.is_paused = False
        self.is_fulltext = False

        self.max_level = 6
        self.topic_substring = ""
        self.message_substring = ""
        self.data_presence_idx = 2
        self.filter = None
        self.update_filter() #header filter
        for man in self.log_mans:
            self.log_mans[man].fill_queue(-1,self.filter)

        self.last_printed_date = "000"

        self.new_entries = 0 #keep track of new entries added while paused
    def prettify_entry(self, fpath:str, log_entry: orea_core.LogEntry, max_message_size=50, full_output=False,
                       stream=sys.stdout):
        """generate rich text representing a specific entry"""
        fpath = os.path.abspath(fpath)
        date_split = log_entry.date.split(" ")
        pretty_string = R"[link][bold]{}[/bold] [bold lime]{}[/bold lime][/link] | ".format(date_split[0],
                                                                                            date_split[1])
        if log_entry.level <= 5:
            pretty_level = "[{}]{}[/{}] | ".format(LOG_EVENT_COLORS[log_entry.level],
                                                   LogLevels(log_entry.level).name,
                                                   LOG_EVENT_COLORS[log_entry.level])
            pretty_string += pretty_level
        else:
            pretty_level = "[bold]{}[/bold] | ".format(log_entry.level)
            pretty_string += pretty_level

        if len(log_entry.message) > max_message_size and full_output == False:
            pretty_string += "{} | {}..".format(log_entry.topic, log_entry.message[:max_message_size])
        else:
            pretty_string += "{} | {}".format(log_entry.topic, log_entry.message)

        if log_entry.dic_extension[1] != 0:
            if full_output == False:
                pretty_string += " | [bold][italic][bright_magenta] + DATA [/bold][/italic][/bright_magenta]"
                return pretty_string
            else:
                d = self.log_mans[fpath].get_content(log_entry)
                return pretty_string + "\n {} \n".format(d)
        return  pretty_string

    def update_filter(self):

        self.filter =  default_header_func(self.max_level,BoolOps.LESS_OR_EQUAL,self.topic_substring,
                                      self.message_substring,LogController.tribool[self.data_presence_idx])

    def print_deque(self,fpath):
        fpath = os.path.abspath(fpath)
        for entry in self.log_mans[fpath].queue :
            try :
                rich.print(self.prettify_entry(fpath,entry,full_output = self.is_fulltext))
            except ValueError :
                self.log_mans[fpath].search_date(entry.date)
                rich.print(self.prettify_entry(fpath, entry, full_output=self.is_fulltext))
                self.log_mans[fpath].search_date(self.log_mans[fpath].queue[-1])


    def print_until_last(self,fpath):

        fpath = os.path.abspath(fpath)
        mv = self.log_mans[fpath].move(1)
        if mv is None : #case when already at EoF
            return
        entry = self.log_mans[fpath].current_entry()
        if entry is None :
            return

        date_prev_entry = entry.date
        if date_prev_entry == self.last_printed_date :
            return

        while True :
            try :
                rich_text = (self.prettify_entry(fpath,entry, full_output=self.is_fulltext))
            except ValueError : #frequent calls might cause the last line of the entry to be cut
                rich_text = (self.prettify_entry(fpath, entry, full_output=False)) + "[bold bright_red blink] (Err.Parsing)[/bold bright_red blink]"
            finally:
                rich.print(rich_text)
                self.last_printed_date = entry.date
                mv = self.log_mans[fpath].move(1)
                if mv is None :
                    return
                entry = self.log_mans[fpath].current_entry()
                if entry.date == self.last_printed_date :
                    return

    def print_all_to_date(self):

        pass
        # log_keys = self.log_mans.keys()
        # logs = np.array([self.log_mans[key].current_entry() for key in log_keys])
        # dates = np.array([l.date for l in logs])
        # while not logs


    def print_plaintext(self,fpath):
    
        fpath = os.path.abspath(fpath)
        self.log_mans[fpath].jump_last()
        entry = self.log_mans[fpath].current_entry()
        
        if entry is not None and self.filter(entry) ==True  :
            if self.last_entry_printed is None or self.last_entry_printed != entry:
                print(entry)
                self.last_entry_printed = entry


