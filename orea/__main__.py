import sys, os
import curses
import inotify.adapters
from .logcontroller import  LogController
from . import orea_core

def on_notify_func(controller) :

    i = inotify.adapters.Inotify(controller.log_mans.keys())
    for event in i.event_gen(yield_nones=False):
      (_, type_names, path, filename) = event
      if "IN_MODIFY" in type_names :
        controller.print_until_last(path+'/'+filename)

if __name__=="__main__" :
    con = LogController(sys.argv[1:])
    on_notify_func(con)