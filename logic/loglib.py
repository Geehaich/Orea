import os

import yaml
from enum import Enum
from threading import current_thread
from datetime import datetime
from collections import deque
import numpy as np
import glm

log_levels = ["FATAL", "ERROR", "WARNING", "INFO", "DEBUG"]

class YAMLDoubleReader :
    """Combine a binary and UTF-8 compatible file wrappers to allow backwards seeking"""
    def __init__(self,file):

        self._bin_io = open(file,"rb")
        self.utf_io = open(file,"r")

    def tell(self):
        return self.utf_io.tell()

    def seek(self,offset,pos):
        bin_position = self._bin_io.seek(offset,pos)
        return self.utf_io.seek(bin_position,0)
    def read(self,bytes = 1):
        res = self.utf_io.read(bytes)
        self._bin_io.seek(self.tell(),0)
        return res
    def readline(self,size=-1):
        res = self.utf_io.readline(size)
        self._bin_io.seek(self.tell(), 0)
        return res
    def read_lines(self,lines = 1):
        count = 0
        result = ""
        for i in range(lines) :
            result+=self.utf_io.readline()
        self._bin_io.seek(self.utf_io.tell(),0)
        return result

    def previous_line_bytes(self,bytes = -1):
        """return the bytes between current position and previous \n, places the cursor on previous \n.
        Returns None if called on the first line"""

        #case of first line
        if self.tell()<=2 :
            self.seek(0,0)
            return None

        #start position is \n, jump over
        self.seek(-2,1)
        start_pos = self.tell()

        #iterate until previous \n or start of file
        cur_char = b'0'
        while self._bin_io.tell() >= 2 and cur_char!=b"\n":
            cur_char = self._bin_io.read(1)
            self._bin_io.seek(-2,1)

        #if not file start go back over \n to contain file
        if cur_char ==b'\n':
            self._bin_io.seek(2,1)
        if(self._bin_io.tell() <=2):
            self._bin_io.seek(0,0)

        global_pos = self._bin_io.tell()
        result_line = None
        if bytes == -1 :
            result_line = self._bin_io.read(start_pos-global_pos+1)
        else :
            result_line = self._bin_io.read(bytes)

        self._bin_io.seek(global_pos,0)
        self.utf_io.seek(global_pos,0)
        return result_line


    def previous_document_extension(self):
        """iterates backwards in file until next iteration of YAML document sign (---).
            sets the stream offset to the beginning of document.
            returns the position of both ends of said document."""

        self.previous_line_bytes() #go over ---
        lower_pos = self._bin_io.tell()

        prev_line = b'0'
        upper_pos = self._bin_io.tell()
        while (prev_line is not None and prev_line !=b'---'):
            prev_line = self.previous_line_bytes()
            upper_pos = self._bin_io.tell()

        if prev_line ==b'---':
            self.readline()
            upper_pos = self._bin_io.tell()
        self.utf_io.seek(upper_pos,0)

        return (upper_pos,lower_pos-upper_pos)

    def next_document_extension(self):
        """iterates forward until next yaml document delimiter. the extension covers the delimiter for consistency
        with previous_document_extension, the --- will need to be removed during deserialization"""
        upper_pos =self._bin_io.tell()
        next_line = next_line = self.readline()
        lower_pos = self._bin_io.tell()
        while(next_line!="" and not next_line.startswith("---")):
            next_line = self.readline()
            lower_pos = self._bin_io.tell()

        self.utf_io.seek(self._bin_io.tell(),0)
        return (upper_pos,lower_pos-upper_pos)


class LogManager :

    def __init__(self, logfile_path):

        self._reader = YAMLDoubleReader(logfile_path)
        self._writer = open(logfile_path,"a")
        self.current_doc_extend = None
        self.jump_last()

    def new_log(self,level,message,optional_dict = {}):
        date = datetime.now()
        thread = current_thread()
        thread_str = "{0} | {1}".format(thread.name,thread.ident)
        yam_dict = {"date": date, "level": level, "thread": thread_str, "message": message, "optional_dict": optional_dict}
        yaml.dump(yam_dict,self._writer)
    def peek(self):
        """checks date and log level without deserializing the rest of an entry"""
        byte_arr = self._reader.read(41) #date and level are fixed size in our format
        if len(byte_arr)<41:
            return (0,-1) #error state, most likely caused by EoF
        date_bytes = byte_arr[6:32] #date is YYYY-MM-DD hh:mm:ss:uuuu , array comparison is equivalent to date comparison
        level_byte = byte_arr[40]

        self._reader.seek(-41,1) #go back to previous position
        return (date_bytes,int(level_byte))

    def move(self,amount):
        xtend = self.current_doc_extend
        if amount >0:
            for i in range(amount):
                xtend = self._reader.next_document_extension()
        elif amount <0 :
            if self._reader.tell()==0: #case of first entry
                self.current_doc_extend = self._byte_jump(0)
                return
            for i in range(-amount):
                xtend = self._reader.previous_document_extension()
        self.current_doc_extend =xtend
    def _byte_jump(self, byte_position):
        """go to the beginning of the document containing a given byte position"""
        self._reader.seek(byte_position,0)
        self._reader.previous_document_extension() #move to beginning of document
        self.current_doc_extend = self._reader.next_document_extension() #move to end to get full extension
        self._reader.seek(self.current_doc_extend[0],0) #back to beginning

    def jump_last(self):
        """get latest entry"""
        self._reader.seek(0,2)
        self.current_doc_extend = self._reader.previous_document_extension()

    def jump_first(self):
        """get first entry"""
        self._reader.seek(0,0)
        self.current_doc_extend = self._reader.next_document_extension()

    def deserialize(self):
        """deserialize current file as YAML object and replaces the offset back at the beginning of the document"""

        if self.current_doc_extend is None :
            return None
        self._reader.seek(self.current_doc_extend[0],0)
        content = self._reader.read(self.current_doc_extend[1])
        if content.endswith("---\n"):
            content = content[:-4]

        self._reader.seek(self.current_doc_extend[0],0)
        return yaml.load(content,yaml.Loader)

    def document_string(self):
        self._reader.seek(self.current_doc_extend[0],0)
        content = self._reader.read(self.current_doc_extend[1])
        if content.endswith("---\n"):
            content = content[:-4]

        self._reader.seek(self.current_doc_extend[0], 0)
        return content

    def goto(self,date):
        """search of entry with date closest to given. first using dichotomy to get closer then iterating over a few
        entries to place the stream at the closest.

        Date is a datetime object or the ISO string representation of one.
        Returns nothing"""
        targ_date = str(date)

        cur_position= self.current_doc_extend[0]
        max_byte = self._reader.seek(0,2) #check file byte count
        self._reader.seek(cur_position,0)

        soon_bound = 0
        late_bound = max_byte

        cur_date = self.peek()[0]
        dc_stop_condition = False

        while not dc_stop_condition :
            cur_date = self.peek()[0]
            cur_position = self._reader.tell()
            if cur_date == targ_date :
                return
            elif cur_date > targ_date :
                late_bound =  cur_position
            elif cur_date < targ_date :
                soon_bound = cur_position
            self._byte_jump((soon_bound+late_bound)//2)

            loop_position = self._reader.tell()
            if loop_position == cur_position :
                dc_stop_condition = True


        if cur_date < targ_date :
            while cur_date < targ_date :
                self.move(1)
                cur_date = self.peek()[0]
            self.move(-1)
        elif cur_date > targ_date :
            while cur_date > targ_date :
                self.move(-1)
                cur_date = self.peek()[0]
            self.move(1)


    def slice_any(self,up:int,down:int):
        """return a list of deserialised entries starting from the current position in both directions"""
        start_exten = self.current_doc_extend
        up_slice = []
        for i in range(up) :
            self.move(-1)
            content = self.deserialize()
            if content is not None:
                up_slice.insert(0,self.deserialize()) #put at beginning to keep order


        self._reader.seek(start_exten[0],0)
        self.current_doc_extend = start_exten
        down_slice = []
        content = self.deserialize()
        if content is not None :
            down_slice.append(content)
        for i in range(down) :
            self.move(2)
            content = self.deserialize()
            if content is not None:
                down_slice.append(content)

        Lm._reader.seek(start_exten[0] if start_exten is not None else 0,0)
        self.current_doc_extend = start_exten
        return up_slice+down_slice

    def slice_conditional(self,max_up:int,max_down:int,peek_func = None,serial_func = None):
        """return a subset of entries in a slice around the current one meeting 2 criteria :
            - one on the date and level , peek_func(self.peek) == true (avoids deserialization for simple date search
            - one on the actual content (thread, and optional dict)"""


        start_exten = self.current_doc_extend
        up_slice = []
        for i in range(max_up):
            self.move(-1)  #go up the file
            head = self.peek()
            criteria_met = True
            content = None
            if peek_func is not None :  #check header against discriminating function if it exists
                criteria_met = criteria_met and peek_func(head)
            if serial_func is not None  and criteria_met == True: #if header is OK and a function exists for deserialized entries check results
                content = self.deserialize()
                criteria_met = criteria_met and serial_func(content)

            if criteria_met== True :
                content = self.deserialize()
                if content is not None :
                    up_slice.insert(0,content)

        self._reader.seek(start_exten[0],0)
        self.current_doc_extend = start_exten

        down_slice = []

        for i in range(max_down+1):

            if i==0: #handle center of slice here by not moving on first call
                self.move(2)
            head = self.peek()
            criteria_met = True
            content = None
            if peek_func is not None:
                criteria_met = criteria_met and peek_func(head)
            if serial_func is not None and criteria_met == True:  # if header is OK and the function exists check for actual content
                content = self.deserialize()
                criteria_met = criteria_met and serial_func(content)

            if criteria_met== True:
                content = self.deserialize()
                if content is not None:
                    down_slice.append(content)

        self._reader.seek(start_exten[0], 0) #back to original entry
        self.current_doc_extend = start_exten

        return up_slice + down_slice





if __name__=="__main__" :

    def basic_peek_func(header) :
        return header[1] ==0
    def basic_serial_func(entry) :
        return entry is not None and "b" in entry["optional_dict"].keys()


    Lm = LogManager("/home/guillaume/repos/Orea/tests/grotest.yaml")
    Lm.goto("2022-12-06 10:08:51.978201")
    Sh = Lm.slice_conditional(15,15,basic_peek_func)
    Sc = Lm.slice_conditional(60,60,None,basic_serial_func)

