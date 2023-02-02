import datetime
import sys
sys.path.append("../")
import curses
from curses import wrapper
from textwrap import TextWrapper
from orea.logcontroller import LogController
from orea.cursed.subwins import timewindow_select,date_select,get_str_bottom_line, help_win
from threading import Lock

DATE_FOREGROUND = curses.COLOR_GREEN|curses.A_BOLD
OPTIONAL_DATA_FOREGROUND = curses.COLOR_BLUE|curses.A_DIM
MIN_COLUMNS = 80
PAD_HEIGHT = 1024
LAST_LINE_OFFSET = 3
MIN_LINES = 35
HEADER_WIDTH = 39 # all lines start with a fixed header incating data presence, date and level, e.g : +DATA | YY-MM-DD hh:mm:ss.mmm | FATAL |



class CP:
    """Class used to initiate a few color pairs and formats, and keep references to them"""
    ERR =  LEVEL_FATAL =None
    LEVEL_ERROR  =None
    LEVEL_WARN  =None
    LEVEL_INFO  =None
    LEVEL_DEBUG  =None
    LEVEL_TRACE  = 0
    DATE  = None
    OPTIONAL_DATA  =None

    STRING_LEVELS = ["FATAL", "ERROR", "WARN ", "DEBUG", "TRACE", "INFO "]
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

    def __init__(self, pathlist_or_logcon):
        """a main application window based on curses
        parameter :
        pathlist_or_logcon : list of filepaths or LogControllerObject"""
        self.screen = curses.initscr()
        self.windims = self.screen.getmaxyx()
        self.pad = curses.newpad(PAD_HEIGHT,self.windims[1])
        curses.start_color()
        CP.init_color_pairs()
        self.screen.keypad(True)
        curses.noecho()
        self.wrapper = TextWrapper(subsequent_indent="\t",width=self.windims[1])
        self.wrapper.initial_indent = HEADER_WIDTH * " "

        self.controller = None
        if type(pathlist_or_logcon) == LogController :
            self.controller = pathlist_or_logcon
        elif type(pathlist_or_logcon) == list :
            self.controller = LogController(pathlist_or_logcon)

        self.paused = False
        self.new_ents = 0

        self.thread_lock = Lock()

        self.end_notify_thread = False

        self._highest_line = PAD_HEIGHT-LAST_LINE_OFFSET #lowest y value with actual text printed
        self._cur_scroll_index = PAD_HEIGHT-LAST_LINE_OFFSET- self.windims[0] #lowest y value on screen (top line)

        self.cur_disp_func = self.output_entry_short
        self.refresh_entries()
        self.statusprint()



    def __del__(self):

        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()

    def key_bindings(self,char):
        """dispatch function for input characters.

        parameters :

        int char : character returned by a getch() call"""

        self.pad.clear()
        if char == curses.KEY_RESIZE :
            self.screen.clear()
            self.windims = self.screen.getmaxyx()
            self.screen.resize(*self.windims)
            self.pad.resize(PAD_HEIGHT, self.windims[1])
            self.wrapper.width = self.windims[1]-1
            if self.windims[0]<10 and self.windims[1] < 50 :
                curses.resizeterm(10,60)

        elif char== curses.KEY_UP :
            self.pause()
            self.controller.scroll(-1)

        elif char== curses.KEY_DOWN :
            self.pause()
            self.new_ents = 0
            self.controller.scroll(1)

        elif char== 337: #SHIFT + KEY_UP
            self.pause()
            self.controller.scroll(-5)
        elif char== 336 : #SHIFT + KEY_DOWN
            self.pause()
            self.controller.scroll(5)
        elif char ==  curses.KEY_PPAGE :
            self.window_scroll(-5)
        elif char == curses.KEY_NPAGE:
            self.window_scroll(5)

        elif char == ord(' '):
            if self.paused :
                self.unpause()
            else :
                self.pause()


        elif char == curses.KEY_LEFT :
            new_level = max(self.controller.max_level-1,0)
            if new_level != self.controller.max_level :
                self.controller.max_level = new_level
                self.controller.update_filter()
        elif char == curses.KEY_RIGHT :
            new_level = min(self.controller.max_level+1,99)
            if new_level != self.controller.max_level :
                self.controller.max_level = new_level
                self.controller.update_filter()

        elif char == ord("d") :
            self.pause()
            self.controller.search_date(date_select(self))

        elif char == 4 : #CTRL+d
            self.controller.set_timeout(timewindow_select(self))

        elif char == curses.KEY_HOME :
            self.pause()
            self.controller.jump_first()
        elif char == curses.KEY_END:
            self.controller.jump_last()

        elif char == 20 : #CTRL+t
            substring = get_str_bottom_line(self,"search topic (* for all): ", self.controller.topic_substring)
            if substring == "*" :
                self.controller.topic_substring = ""
                self.controller.update_filter()
            else :
                if substring not in ["",self.controller.topic_substring] :
                    self.controller.topic_substring = substring
                    self.controller.update_filter()

        elif char == 6 : #CTRL+f
            substring = get_str_bottom_line(self,"search message (* for all): ",self.controller.message_substring)
            if substring == "*" :
                self.controller.message_substring = ""
                self.controller.update_filter()
            else:
                if substring not in ["",self.controller.message_substring]:
                    self.controller.message_substring = substring
                    self.controller.update_filter()

        elif char == curses.KEY_F1 :
            help_win(self)

        elif char == ord('+'):
            self.change_display_mode()


        self.refresh_entries()
        self.statusprint()
        self.screen.refresh()
    def output_head(self,entry ,show_data=True):
        """write first fields of an entry to the screen using appropriate colors."""
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
        if entry.level < 6:
            self.pad.addstr(CP.STRING_LEVELS[entry.level], CP.LIST_CP[entry.level])
        else:
            self.screen.addstr(str(entry.level))
        self.pad.addstr(" | ")

    def output_entry_short(self,entry) -> int :
        """write an entry as simplified syntax on current line, accounting for terminal width. returns the row value
        for coherence with output_entry_long"""

        if entry is None :
            return self.pad.getyx()[0]


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
        if entry is None :
            return

        if y == 0 :
            self.output_entry_short(entry)
            return
        d = entry.deserialize()
        string_towrap = "{} | {} ".format(entry.topic, entry.message)

        self.wrapper.width = self.windims[1]
        wraparray = self.wrapper.wrap(string_towrap)
        last_nondict_idx = len(wraparray)
        if d is not None :
            str_d = str(d)
            self.wrapper.initial_indent = (6)*' '
            wraparray += self.wrapper.wrap(str_d)
            self.wrapper.initial_indent = (HEADER_WIDTH)*' '

        wraparray [0] = wraparray[0][HEADER_WIDTH:] #remove spaces from first line

        if y-len(wraparray) <0 :
            self.output_entry_short(entry) #overwrite previous head
            return y

        self.pad.move(y-len(wraparray),0)
        self.output_head(entry)
        self.pad.addstr(wraparray[0])
        for i in range(1,len(wraparray)) :
            if i < last_nondict_idx :
                self.pad.addstr(y-len(wraparray)+i,0,wraparray[i])
            else :
                self.pad.addstr(y-len(wraparray)+i,0,wraparray[i],curses.color_pair(0)|curses.A_BOLD) #print dict content as different color

        return y-len(wraparray)+1

    def refresh_entries(self):
        """refresh screen with current list of entries using the currently selected output function"""

        try :
            self.pad.clear()
            if self.cur_disp_func == self.output_entry_short:
                self.pad.move(PAD_HEIGHT-LAST_LINE_OFFSET-3,0)
            else :
                self.pad.move(PAD_HEIGHT - LAST_LINE_OFFSET - 2, 0)
            high = PAD_HEIGHT-LAST_LINE_OFFSET
            if self.controller.contents_changed :
                self.controller.collect_entries()
            for entry in self.controller.sorted_entries :
                high = self.cur_disp_func(entry)
                if high == 0 :
                    break
                else :
                    self.pad.move(high-1,0)

            self._highest_line = high
            if self._highest_line >= PAD_HEIGHT-LAST_LINE_OFFSET- self.windims[0] :
                self._cur_scroll_index = PAD_HEIGHT-LAST_LINE_OFFSET- self.windims[0]
            else :
                self._cur_scroll_index = max(self._cur_scroll_index,self._highest_line)

            self.pad.refresh(self._cur_scroll_index,0,0,0,self.windims[0]-LAST_LINE_OFFSET,self.windims[1])

        except :
            self.screen.clear()
            self.screen.addstr(0,0,"printing entries failed, please resize window and press any key")

    def window_scroll(self,amount):
        """scroll along window if the total list of entries takes more lines than displayed on screen"""
        self._cur_scroll_index += amount
        self._cur_scroll_index = max(self._cur_scroll_index,self._highest_line)
        self._cur_scroll_index = min(self._cur_scroll_index,PAD_HEIGHT-LAST_LINE_OFFSET-self.windims[0])

        self.pad.refresh(self._cur_scroll_index-1, 0, 0, 0, self.windims[0] - LAST_LINE_OFFSET, self.windims[1])

    def statusprint(self):
        """print relevant info such as current max level or pause status on the sedond last line of the screen."""
        try :
            self.screen.move(self.windims[0]-2,0)
            self.screen.clrtoeol()
            self.screen.addstr("    MAX LV : ")
            if self.controller.max_level < 6 :
                self.screen.addstr(CP.STRING_LEVELS[self.controller.max_level], CP.LIST_CP[self.controller.max_level])
            else :
                self.screen.addstr(str(self.controller.max_level))
            self.screen.addstr("    DISP : ")
            if self.cur_disp_func == self.output_entry_short :
                self.screen.addstr("SHRT",curses.color_pair(0)|curses.A_NORMAL)
            else:
                self.screen.addstr("FULL",curses.color_pair(0)|curses.A_REVERSE)

            self.screen.addstr("    EST. POS : ",CP.LEVEL_INFO)
            mp = self.controller.mean_position()
            if mp<10 :
                self.screen.addch(" ")
            self.screen.addstr(str(mp)+"%  ")

            if self.paused :
                self.screen.addstr("||",curses.color_pair(0)|curses.A_REVERSE)
                self.screen.addstr("  ")
                if self.new_ents !=0 :
                    self.screen.addstr(str(self.new_ents) + "new")

            l_up,l_down = self.controller.is_search_zone_limit()
            if self.paused and (l_up or l_down ):
                self.screen.addstr("  SRCH TMOUT")



        except : #window probably too short. function not that important, can afford ignoring exceptions
            pass

    def key_bind_threadfunc(self):
        """wrap keyboard interaction in a single function to call it inside threads"""

        cur_key = 0
        while cur_key != ord("q"):
            self.thread_lock.acquire()
            try:
                self.key_bindings(cur_key)
            finally:
                self.thread_lock.release()
                cur_key = self.screen.getch()

        self.end_notify_thread = True


    def pause(self):
        if not self.paused :

            self.paused = True
            self.new_ents = 0

    def unpause(self):
        if  self.paused :
            self.paused = False
            self.new_ents = 0
            self.controller.jump_last()

    def on_file_mod_event(self):
        """function called when a file event is raised by Inotify. either scrolls until the last entries available (live)
        or increments the new entry counter (paused)"""
        if self.paused == False:
            while not self.controller.all_eof() and self.paused == False:
                self.thread_lock.acquire()
                self.controller.scroll(1,inf_scroll=True)
                self.controller.collect_entries()
                self.refresh_entries()
                self.statusprint()
                self.thread_lock.release()
        else :
            self.thread_lock.acquire()
            self.new_ents +=1
            self.statusprint()
            self.thread_lock.release()



    def change_display_mode(self):
        """toggle full or short entry display mode"""
        if self.cur_disp_func == self.output_entry_short :
            self.cur_disp_func = self.output_entry_long
            return
        else :
            self.cur_disp_func = self.output_entry_short
