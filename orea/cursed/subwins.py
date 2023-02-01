import curses
from datetime import timedelta
import curses.textpad


def date_select(win ) -> str :
    """quick widget allowing the user to select a date and time and returning it as an ISO date string"""
    init_date = win.controller.sorted_entries[0].date

    time_array = [int(init_date[0:4]), int(init_date[5:7]), int(init_date[8:10]),int(init_date[11:13]),
        int(init_date[14:16]), int(init_date[17:19]), int(init_date[20:])]
    modulos = [10000,13,32,24,60,60,1000000]
    selection_index = 5

    char = 0
    win.screen.move(win.windims[0] - 1, 0)
    win.screen.clrtoeol()
    date_head = "pick date : "
    win.screen.addstr(date_head)
    while True :

        if char == curses.KEY_UP :
            time_array[selection_index] += 1 if selection_index!= 6 else 1000
            time_array[selection_index] %= modulos[selection_index]
            if time_array[selection_index]==0 and selection_index <=2 :
                time_array[selection_index]+=1
            if selection_index == 6 :
                time_array[selection_index] = round(time_array[selection_index]/1000)*1000

        if char == curses.KEY_DOWN :
            time_array[selection_index] -= 1 if selection_index!= 6 else 1000
            time_array[selection_index] %= modulos[selection_index]
            if selection_index == 6 :
                time_array[selection_index] = round(time_array[selection_index]/1000)*1000
            if time_array[selection_index] == 0 and selection_index <= 2:
                time_array[selection_index] = modulos[selection_index]-1
        if char == curses.KEY_LEFT :
            selection_index = (selection_index-1)%7
        if char == curses.KEY_RIGHT :
            selection_index = (selection_index+1)%7

        win.screen.move(win.windims[0]-1,len(date_head))
        win.screen.addstr(f"{time_array[0]:0>4}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==0 else curses.A_DIM))
        win.screen.addstr("-")
        win.screen.addstr(f"{time_array[1]:0>2}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==1 else curses.A_DIM))
        win.screen.addstr("-")
        win.screen.addstr(f"{time_array[2]:0>2}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==2 else curses.A_DIM))
        win.screen.addstr(" ")
        win.screen.addstr(f"{time_array[3]:0>2}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==3 else curses.A_DIM))
        win.screen.addstr(":")
        win.screen.addstr(f"{time_array[4]:0>2}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==4 else curses.A_DIM))
        win.screen.addstr(":")
        win.screen.addstr(f"{time_array[5]:0>2}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==5 else curses.A_DIM))
        win.screen.addstr(".")
        win.screen.addstr(f"{time_array[6]:0>3}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==6 else curses.A_DIM))

        if char == curses.KEY_ENTER or char ==10 or char ==13 : # enter, \n or \r
            win.screen.move(win.windims[0] - 1, 0)
            win.screen.addstr(" "*38)
            return f"{time_array[0]:0>4}-{time_array[1]:0>2}-{time_array[2]:0>2} {time_array[3]:0>2}:{time_array[4]:0>2}:{time_array[5]:0>2}.{time_array[6]:0>2}"

        char = win.screen.getch()

def timewindow_select(win ) -> str :
    """asks the user for an interval for search timeouts"""
    curses.curs_set(0)

    days, mins,secs = win.controller.search_timeout.days, win.controller.search_timeout.seconds //60 , win.controller.search_timeout.seconds %60
    hours = win.controller.search_timeout.seconds //3600
    mins = (win.controller.search_timeout.seconds -hours*3600) //60
    secs = win.controller.search_timeout.seconds %60

    time_array = [days,hours,mins,secs]
    modulos = [7,24,60,60]
    selection_index = 2

    char = 0
    win.screen.move(win.windims[0] - 1, 0)
    win.screen.clrtoeol()
    date_head = "search time interval : "
    win.screen.addstr(date_head)
    while True :

        if char == curses.KEY_UP :
            time_array[selection_index] += 1
            time_array[selection_index] %= modulos[selection_index]

        if char == curses.KEY_DOWN :
            time_array[selection_index] -= 1
            time_array[selection_index] %= modulos[selection_index]
        if char == curses.KEY_LEFT :
            selection_index = (selection_index-1)%4
        if char == curses.KEY_RIGHT :
            selection_index = (selection_index+1)%4

        win.screen.move(win.windims[0]-1,len(date_head))
        win.screen.addstr(f"{time_array[0]}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==0 else curses.A_DIM))
        win.screen.addstr(" days+ ")
        win.screen.addstr(f"{time_array[1]:0>2}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==1 else curses.A_DIM))
        win.screen.addstr(":")
        win.screen.addstr(f"{time_array[2]:0>2}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==2 else curses.A_DIM))
        win.screen.addstr(":")
        win.screen.addstr(f"{time_array[3]:0>2}",curses.color_pair(0)|(curses.A_REVERSE if selection_index ==3 else curses.A_DIM))

        if char == curses.KEY_ENTER or char ==10 or char ==13 : # enter, \n or \r
            win.screen.move(win.windims[0] - 1, 0)
            win.screen.clrtoeol()
            curses.curs_set(1)
            return timedelta(days = time_array[0],hours = time_array[1], minutes= time_array[2], seconds = time_array[3])

        char = win.screen.getch()
def get_str_bottom_line(win, askinput : str,init ="") -> str :
    """input field at the last line of the window"""
    win.screen.move(win.windims[0]-1,0)
    win.screen.addstr(askinput)
    x = win.screen.getyx()[1]
    win.screen.refresh()
    editwin = curses.newwin(1,255,win.windims[0]-1,x)
    editwin.addstr(init[:255])
    tbox = curses.textpad.Textbox(editwin)
    tbox.edit()
    res = tbox.gather().strip()
    win.screen.move(win.windims[0]-1,0)
    win.screen.clrtoeol()

    return res


def help_win(win) :
    """print a formatted reminder of the window's controls"""
    try :
        win.screen.clear()
        win.screen.addstr(1,13,"---HELP---",curses.color_pair(0)|curses.A_BOLD|curses.A_REVERSE)
        win.screen.addstr(3,3,"▲ ▼ ",curses.color_pair(0)|curses.A_BOLD)
        win.screen.addstr("scroll entries (CTRL+ to scroll 5 by 5)",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(4,3,"◄ ► ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("set maximum log level",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(5,3,"CTRL+F / CTRL+T ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("Filter by message / topic content",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(6,3,"d ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("search date",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(7,3,"CTRL+d ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("set search timeout (stop looking for entries when the next one is further than this",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(8,3,"HOME / END ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("go to first / latest entries",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(9,3,"SPACE ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("pause. resuming also goes to latest entries",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(10,3,"PG.UP / PG.DOWN ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("scroll window if content buffer contains more lines than terminal",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(11,3,"+ ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("switch between visualisation modes (FULL takes more resources to deserialize entries)",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(12, 3, "q ", curses.color_pair(0) | curses.A_BOLD)
        win.screen.addstr("quit program",curses.color_pair(0) | curses.A_DIM)
        win.screen.addstr(15,2,"press SPACE to return",curses.color_pair(0) | curses.A_REVERSE)
        win.screen.refresh()
        while win.screen.getch() != ord(" ") :
            continue
    except Exception as E :
        pass