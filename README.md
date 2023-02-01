#Orea

Orea is a logging library allowing you to append additional data to your entries. 

- Serialize applicable data and append it to entries.
- Parse through large files to locate specific entries
- Filter entries according to  content
- use a basic CLI to monitor new entries in real time


## How it works 

 ![YAML representation of entry](/home/guillaume/Images/yaml_example.png) 
 
 entries are represented as above, in multidocument YAML files. Each has mandatory fields **(date, topic,message & level) ** making up an entry header, and anything past those is considered an optional payload.
 
 
We provide through our rust API a **LogManager** struct used to parse those files and detect relevant document boundaries, either by moving incrementally along the file or using a dichotomical date search, and a **LogManagerWrapper** class in our Python API wrapping the previous one, containing a deque to keep a rolling amount of entries, and providing you with a method to write new entries in the same file.

the following code details the class' base functions.
 
 
``` 
from orea import LogManagerWrapper
from datetime import datetime,timedelta


#declaration, basic movement

log_manager = LogManagerWrapper("/foo/bar/log.yaml",deque_max_len = 15) #create a LogManager which will parse the file
log_manager.jump_first(refill=True) #move to beginning of file and search down for entries until 15 reached or the scroll function times out.
log_manager.search_date("2023-01-30 19:18:08.248381") #search for last entry with an earlier date than this
log_manager.move_doc(3)#move 3 entries down


#scrolling along file

    #simple header filtering function
def head_filter(e : LogEntry) -> bool :
    return e.level <= 2 and "foo" in e.message

    #simple content filtering function
def con_filter(e : LogEntry) -> bool :
    dic = e.deserialize()
    return "a" in dic.keys() and dic[a] % 17 == 0 


log_manager.search_timeout = timedelta(seconds = 15) #set search timeout (class default is 180s)
log_manager.scroll(-5,filter,head_filter,con_filter) #move down the file and fill queue with entries matching filter until 5 entries match,
                                                # the first entry in the file is reached, or there's no valid
                                                #entry for 15 seconds worth of entries.

c_entry = log_manager.current_entry() #get entry the cursor is currently pointing to
some_entry  =log_manager.queue[5] #get entry stored in the queue
dic = c_entry.deserialize() #get optional data

log_manager.new_entry("message",3,"topic",{"foo":15,"bar": [1,2,3,["and",0.3]]} #append new entry at the end of tracked file. NB : level is an integer between 0 and 99, it will usually get aliased as a classic level by other parts of the lib if level<=6
```
 
 
## CLI
 ![Screenshot of the CLI](/home/guillaume/repos/Orea/images/CLI.png) 
 for basic applications, we also provide a command-line viewer. Launching the module as an application with a syntax such as `python -m orea foo/bar.yaml  foo/bar/baz/* ` will start a curses-based interface with basic filtering and scrolling capabilities, which also looks for file modification events to display new entries as the source files are updated.
 
 ![ ](/home/guillaume/repos/Orea/images/help.png  "The interface's commands, type F1 to display this window")
 
 
 
##Misc.
the *tests* folder contains a few scripts to generate files full of random entries to test the base library or the interface's response to file events
 
##Known issues

- CLI crashes if the size of the printout exceeds a hard-coded amount of lines
- CLI crashes if terminal size is too small, will add exception handling later
- CLI may segfault because of race conditions between the keyboard event handling thread and the file event notifying one.
- processing cost depends on amount of tracked files and deque sizes because of sorting, will try changing data structure.
- scrolling takes longer when the search function gets more restrictive, as it attempts to fill each file deque and scrolls increasingly further. Might add a numerical search timeout to supplement the temporal one for high entry densities and low matching densities.
 