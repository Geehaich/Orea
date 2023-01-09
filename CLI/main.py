import sys,os
import curses
import inotify.adapters
from LogController import  LogController
import orea_core

def on_notify_func(controller) :

    i = inotify.adapters.Inotify(controller.log_mans.keys())
    for event in i.event_gen(yield_nones=False):
      (_, type_names, path, filename) = event
      if "IN_CLOSE_WRITE" in type_names :
        controller.print_last(path+'/'+filename)



#debug in console for now
if __name__=="__main__" :


    fpaths = [os.path.abspath("./tests/moby1.yaml"),os.path.abspath("./tests/moby2.yaml")]
    con = LogController(fpaths)
    print(con.log_mans.keys())
    on_notify_func(con)