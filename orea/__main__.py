import sys, os
import curses
import inotify.adapters
import threading
from .logcontroller import  LogController
from .cursed.mainwin import CMainWindow

from numpy.random import randint

def on_notify_func(window) :
    i = inotify.adapters.Inotify(window.controller.log_mans.keys())
    for event in i.event_gen(yield_nones=True):
        if window.end_notify_thread  :
            return
        if event is not None :
            (_, type_names, path, filename) = event
            if "IN_MODIFY" in type_names :
                window.on_file_mod_event()
                window.screen.refresh()

if __name__=="__main__" :
    con = LogController(sys.argv[1:])
    win = CMainWindow(con)
    tkey = threading.Thread(target = win.key_bind_threadfunc)
    tnot = threading.Thread(target= on_notify_func,args = [win])
    tkey.start()
    tnot.start()
    tnot.join()

