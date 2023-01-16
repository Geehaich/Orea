import curses
from curses import wrapper
from enum import Enum
from textwrap import TextWrapper

import sys
sys.path.append("../")
from orea.loglib import LogManagerWrapper,LogLevels

DATE_FOREGROUND = curses.COLOR_GREEN|curses.A_BOLD
OPTIONAL_DATA_FOREGROUND = curses.COLOR_BLUE|curses.A_DIM
MIN_COLUMNS = 60
MIN_LINES = 35

Lm = LogManagerWrapper("../tests/moby/moby2.yaml")
Lm.search_date("2023-01-12 10:01:31.666427")
from numpy.random import randint

class CP:
    ERR =  LEVEL_FATAL =None
    LEVEL_ERROR  =None
    LEVEL_WARN  =None
    LEVEL_INFO  =None
    LEVEL_DEBUG  =None
    LEVEL_TRACE  = 0
    DATE  = None
    OPTIONAL_DATA  =None

    STRINGS_LEVELS = ["FATAL", "ERROR", "WARN ", "DEBUG", "TRACE", "INFO "]
    @classmethod
    def init_color_pairs(cls):
        curses.init_pair(5, curses.COLOR_RED, curses.COLOR_BLACK)
        cls.ERR = curses.color_pair(5) | curses.A_BOLD | curses.A_BLINK
        cls.LEVEL_FATAL = cls.ERR
        curses.init_pair(6, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        cls.LEVEL_ERROR = curses.color_pair(6) | curses.A_BOLD
        curses.init_pair(7, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        cls. LEVEL_WARN = curses.color_pair(7) | curses.A_BOLD
        curses.init_pair(8, curses.COLOR_BLUE, curses.COLOR_BLACK)
        cls.LEVEL_INFO = curses.color_pair(8) | curses.A_BOLD
        curses.init_pair(9, curses.COLOR_CYAN, curses.COLOR_BLACK)
        cls.LEVEL_DEBUG = curses.color_pair(9) | curses.A_BOLD
        cls.LEVEL_TRACE = curses.color_pair(0) | curses.A_BOLD
        curses.init_pair(11,curses.COLOR_GREEN, curses.COLOR_BLACK)
        cls. DATE = curses.color_pair(11) | curses.A_BOLD
        curses.init_pair(12, curses.COLOR_BLUE, curses.COLOR_BLACK)
        cls.OPTIONAL_DATA = curses.color_pair(12) | curses.A_BOLD | curses.A_ITALIC

        cls.LIST_CP = [cls.LEVEL_FATAL, cls.LEVEL_ERROR, cls.LEVEL_WARN,
                       cls.LEVEL_DEBUG, cls.LEVEL_TRACE, cls.LEVEL_INFO]




class CMainWindow :
    """a main application window based on curses"""
    def __init__(self):

        self.screen = curses.initscr()
        self.windims = self.screen.getmaxyx()
        self.screen.resize(max(self.windims[0],30), max(self.windims[1],65))
        self.windims = self.screen.getmaxyx()
        self.pad = curses.newpad(2000,self.windims[1])
        curses.start_color()
        CP.init_color_pairs()
        self.screen.keypad(0)
        curses.noecho()
        #self.controller = LogController(paths)
        self.wrapper = TextWrapper(subsequent_indent="\t",width=self.windims[1])

        cur_key = self.screen.getch()
        while cur_key != ord("q") :
            self.screen.clear()
            self.key_bindings(cur_key)

            cur_key = self.screen.getch()

        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()

    def key_bindings(self,char):

        if char == curses.KEY_RESIZE :
            self.windims = self.screen.getmaxyx()
            self.screen.resize(max(self.windims[0], MIN_LINES), max(self.windims[1], MIN_COLUMNS))
            self.pad.resize(self.pad.getmaxyx()[0], max(self.windims[1], MIN_COLUMNS))
            self.wrapper.width = self.windims[1]-1

        else :

            self.windims = self.screen.getmaxyx()
            self.screen.clear()
            self.screen.move(0,0)
            for i in range(10):
                self.screen.move(i,0)
                Lm.move(randint(-10, 10))
                test_entry = Lm.current_entry()
                self.cursify_entry_short(test_entry)
            # self.screen.addstr(self.windims[0] // 2, self.windims[1] // 2, str("bite\nbite\nbite"), CP.LEVEL_FATAL)
        self.screen.refresh()
            

    def cursify_head(self,entry,show_data=True):
        position = self.screen.getyx()
        self.screen.move(position[0], 0)
        if entry.dic_extension[1] != 0 and show_data:
            self.screen.addstr("+DATA", CP.OPTIONAL_DATA)
            self.screen.addstr(" | ")
        self.screen.addstr(entry.date, CP.DATE)
        self.screen.addstr(" | ")
        if entry.level < 5:
            self.screen.addstr(CP.STRINGS_LEVELS[entry.level], CP.LIST_CP[entry.level])
        else:
            self.screen.addstr(str(entry.level))
        self.screen.addstr(" | ")

    def cursify_entry_short(self,entry) -> int :
        """write an entry as simplified syntax on current line, accounting for terminal width"""

        self.cursify_head(entry)

        x = self.screen.getyx()[1]
        space_left = self.windims[1] - 4 - x
        space_available_topic = int(space_left * len(entry.topic)/(1+len(entry.topic)+len(entry.message)))
        space_available_message = int(space_left * len(entry.message)/(1+len(entry.topic)+len(entry.message)))
        one_line_msg = entry.message.replace('\n'," ")
        if len(entry.topic)>space_available_topic:
            self.screen.addstr(entry.topic[:space_available_topic-3]+"... | ")
        else :
            self.screen.addstr(entry.topic[:space_available_topic]+" | ")
        if len(one_line_msg)> space_available_message:
            self.screen.addstr(one_line_msg[:space_available_message-3]+"...")
        else :
            self.screen.addstr(one_line_msg[:space_available_message])

    def cursify_entry_long(self,entry):



        self.cursify_head(entry,False)

        y,x = self.screen.getyx()
        d = entry.deserialize()
        string_towrap = ""
        if d :
            string_towrap = "{} | {} | {}".format(entry.topic,entry.message,d)
        else :
            string_towrap = "{} | {} ".format(entry.topic, entry.message)


if __name__=="__main__":
    CMainWindow()