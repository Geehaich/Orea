import datetime
import sys
sys.path.append("../")
import curses
from curses import wrapper
from textwrap import TextWrapper
from orea.logcontroller import LogController



DATE_FOREGROUND = curses.COLOR_GREEN|curses.A_BOLD
OPTIONAL_DATA_FOREGROUND = curses.COLOR_BLUE|curses.A_DIM
MIN_COLUMNS = 80
PAD_HEIGHT = 200
MIN_LINES = 35
HEADER_WIDTH = 39 # all lines start with a fixed header incating data presence, date and level, e.g : +DATA | YY-MM-DD hh:mm:ss.mmm | FATAL |


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
    def __init__(self, pathlist_or_logcon):

        self.screen = curses.initscr()
        self.windims = self.screen.getmaxyx()
        self.screen.resize(max(self.windims[0],30), max(self.windims[1],65))
        self.windims = self.screen.getmaxyx()
        self.pad = curses.newpad(PAD_HEIGHT,self.windims[1])
        curses.start_color()
        CP.init_color_pairs()
        self.screen.keypad(True)
        curses.noecho()
        #self.controller = LogController(paths)
        self.wrapper = TextWrapper(subsequent_indent="\t",width=self.windims[1])
        self.wrapper.initial_indent = HEADER_WIDTH * " "

        self.controller = None
        if type(pathlist_or_logcon) == LogController :
            self.controller = pathlist_or_logcon
        elif type(pathlist_or_logcon) == list :
            self.controller = LogController(pathlist_or_logcon)

        self._highest_line = PAD_HEIGHT-1 #lowest y value with actual text printed
        self._cur_scroll_index = PAD_HEIGHT-1- self.windims[0] #lowest y value on screen (top line)

        self.cur_disp_func = self.output_entry_short

        cur_key = self.screen.getch()
        while cur_key != ord("q") :
            self.key_bindings(cur_key)

            cur_key = self.screen.getch()

        curses.nocbreak()

        self.screen.keypad(False)
        curses.echo()
        curses.endwin()

    def key_bindings(self,char):

        self.pad.clear()
        if char == curses.KEY_RESIZE :
            self.windims = self.screen.getmaxyx()
            self.pad.resize(PAD_HEIGHT, self.windims[1])
            self.screen.resize(*self.windims)
            self.wrapper.width = self.windims[1]-1

        elif char== curses.KEY_DOWN :
            self.controller.scroll(1)

        elif char== curses.KEY_UP :
            self.controller.scroll(-1)
        elif char== curses.KEY_PPAGE :
            self.controller.scroll(-5)
        elif char== curses.KEY_NPAGE :
            self.controller.scroll(5)
        elif char== curses.KEY_DOWN :
            self.controller.scroll(1)

        elif char == "F" :
            self.controller.jump_first()
        elif char == "L":
            self.controller.jump_last()
        elif char == '+':
            self.change_display_mode()
        else :
            ents = self.controller.get_sorted_entries()
            self.pad.move(PAD_HEIGHT-1,0)
            h = PAD_HEIGHT-1
            for i in range(25) :
                self.pad.addstr(str(Lm.queue[24-i]))#h = self.output_entry_short(ents[i])
                self.pad.move(h-1,0)
                h-=1
            self.pad.refresh(PAD_HEIGHT-26,0,self.windims[0]-26,0,self.windims[0]-1,self.windims[1])
            self.pad.addstr(0,0,str(datetime.datetime.now()))
            self.pad.refresh(0,0,0,0,2,30)


    def output_head(self,entry ,show_data=True):
        """write first fields of an entry using appropriate colors."""
        position = self.pad.getyx()
        self.pad.move(position[0], 0)
        if entry.dic_extension[1] != 0 and show_data:
            self.pad.addstr("+DATA", CP.OPTIONAL_DATA)
            self.pad.addstr(" | ")
        else :
            self.pad.addstr("-----")
            self.pad.addstr(" | ")
        self.pad.addstr(entry.date[2:-3], CP.DATE)
        self.pad.addstr(" | ")
        if entry.level < 5:
            self.pad.addstr(CP.STRINGS_LEVELS[entry.level], CP.LIST_CP[entry.level])
        else:
            self.screen.addstr(str(entry.level))
        self.pad.addstr(" | ")

    def output_entry_short(self,entry) -> int :
        """write an entry as simplified syntax on current line, accounting for terminal width. returns the row value
        for coherence with output_entry_long"""

        self.output_head(entry)

        y,x = self.pad.getyx()
        space_left = self.windims[1] - 4 - x
        space_available_topic = max(int(space_left * len(entry.topic)/(1+len(entry.topic)+len(entry.message))),4)
        space_available_message = int(space_left * len(entry.message)/(1+len(entry.topic)+len(entry.message)))
        one_line_msg = entry.message.replace('\n'," ")
        if len(entry.topic) > 4 and len(entry.topic)>space_available_topic:
            self.pad.addstr(entry.topic[:space_available_topic-3]+"... | ")
        else :
            self.pad.addstr(entry.topic[:space_available_topic]+" | ")
        if len(one_line_msg)> space_available_message:
            self.pad.addstr(one_line_msg[:space_available_message-3]+"...")
        else :
            self.pad.addstr(one_line_msg[:space_available_message])

        return y #return line for coherence with output_entry_long

    def output_entry_long(self,entry):
        """write a single entry as a multiline string with full message and data if applicable. return the highest row
        it wrote on for subsequent"""

        y,x = self.pad.getyx()
        if y == 0 :
            self.output_entry_short(entry)
            return
        d = entry.deserialize()
        string_towrap = ""
        if d is not None :
            string_towrap = "{} | {} |\n {}".format(entry.topic,entry.message,d)
        else :
            string_towrap = "{} | {} ".format(entry.topic, entry.message)

        self.wrapper.width = self.windims[1]
        wraparray = self.wrapper.wrap(string_towrap)
        wraparray [0] = wraparray[0][HEADER_WIDTH:]
        if y-len(wraparray) <0 :
            self.output_entry_short(entry) #overwrite previous head
            return y

        self.pad.move(y-len(wraparray),0)
        self.output_head(entry)
        self.pad.addstr(wraparray[0])
        for i in range(1,len(wraparray)) :

            self.pad.addstr(y-len(wraparray)+i,0,wraparray[i])

        return y-len(wraparray)

    def output_entries(self):

        self.pad.clear()
        self.pad.move(PAD_HEIGHT-1,0)
        high = PAD_HEIGHT-1
        for entry in self.controller.get_sorted_entries() :
            high = self.cur_disp_func(entry)
            if high == 0 :
                break
            else :
                self.pad.move(high-1,0)

        self._highest_line = high
        if self._highest_line >= PAD_HEIGHT-1- self.windims[0] :
            self._cur_scroll_index = PAD_HEIGHT-1- self.windims[0]
        else :
            self._cur_scroll_index = max(self._cur_scroll_index,self._highest_line)

        self.pad.refresh(self._cur_scroll_index,0,0,0,*self.windims)





    def change_display_mode(self):
        """toggle full or short entry display mode"""
        if self.cur_disp_func == self.output_entry_short :
            self.cur_disp_func = self.output_entry_long
            return
        else :
            self.cur_disp_func = self.output_entry_long

if __name__=="__main__":

    Lc = LogController(["../tests/moby/moby1.yaml"])
    Lm = Lc.log_mans[list(Lc.log_mans.keys())[0]]
    ent = Lc.get_sorted_entries()


    curses.wrapper(lambda x : CMainWindow(Lc))