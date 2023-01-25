from mainwin import CMainWindow
import curses
import curses.textpad


def date_select(win : CMainWindow) -> str :

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


def get_str_bottom_line(win:CMainWindow, askinput : str) -> str :

    win.screen.move(win.windims[0]-1,0)
    win.screen.addstr(askinput,curses.color_pair(0))
    x = win.screen.getyx()[1]
    editwin = curses.newwin(1,255,win.windims[0]-1,x)
    tbox = curses.textpad.Textbox(editwin)
    tbox.edit()
    res = tbox.gather()
    win.screen.move(win.windims[0]-1,0)
    win.screen.clrtoeol()

    return res


