use core::panic;
use std::hash::Hash;
use std::io::{BufReader,BufWriter, Seek, SeekFrom, Read, BufRead,Result};
use std::path::Path;
use std::fs::File;
use pyo3::prelude::*;
use std::{thread, string};
use std::any::Any;
use std::collections::HashMap;

extern crate yaml_rust;
use yaml_rust::{Yaml,YamlLoader, YamlEmitter};
extern crate chrono;
use chrono::{DateTime,Utc};

#[pyclass]
pub struct YAMLReader
{
    bin_reader : BufReader<File>
}

impl std::ops::Deref for YAMLReader
{
    type Target = BufReader<File>;
    fn deref(&self) -> &Self::Target
    {
        &self.bin_reader
    }
}
impl std::ops::DerefMut for YAMLReader
{
    fn deref_mut(&mut self) -> &mut Self::Target
    {
        &mut self.bin_reader
    }
}

impl YAMLReader
{
    pub fn new(filepath : &mut String) -> YAMLReader //get a yaml reader from a given file path
    {
        let path = Path::new(&filepath);
        let bin_file = match File::open(path)
        {
            Err(why) => panic!("couldn't open {} : {}", path.display(), why),
            Ok(file) => file,
        };
        let buf_read = BufReader::new(bin_file);
        
        YAMLReader {bin_reader: buf_read }
    }

    //BufReader::stream_len isn't yet in daily file module, need to implement
    pub fn get_len(&mut self)->Result<u64>
    {
        let init_pos = self.stream_position().unwrap();
        let end_pos = self.seek(SeekFrom::End(0));
        let _r = self.seek(SeekFrom::Start(init_pos));
        end_pos
    }

    //moves back in the stream until a line break character is found, places
    //stream on next byte after \n
    pub fn move_previous_line(&mut self)
    {
        let mut cur_byte  = [b'0'];
        let mut _ru : Result<usize>;
        let mut _r64 : Result<u64>;

        if self.stream_position().unwrap() <= 2 //case beginning of document
        {
            _r64= self.seek(SeekFrom::Start(0));
            return;
        }

        _r64 =self.seek(SeekFrom::Current(-2));

        //read one byte and move back two every time
        while self.stream_position().unwrap() >= 2 && cur_byte[0] != b'\n'
        {
            _ru = self.read(&mut cur_byte);
            print!("{}",cur_byte[0] as char);
            _r64 =self.seek(SeekFrom::Current(-2));
        }

        if cur_byte[0] == b'\n'
        {
            _r64 =self.seek(SeekFrom::Current(2));
        }
        if self.stream_position().unwrap()<=2
        {
            _r64 =self.seek(SeekFrom::Start(0));
        }
        
        let global_pos = self.stream_position().unwrap();
        _r64 =self.seek(SeekFrom::Start(global_pos));


    }

    ///read N bytes in either direction from the current position
    fn read_nbytes(&mut self,n : i64) -> Vec<u8>
    {
        let cur_pos = self.stream_position().unwrap();
        let max_pos = self.get_len().unwrap();
        
        if n>0
        {
            let len = ((max_pos-cur_pos) as i64).min(n);
            let mut result = Vec::<u8>::with_capacity(len as usize);
            let _x = self.read(&mut result);
            result
        }
        else if n<0
        {
            let len = 0.max(cur_pos as i64 +n);
            let mut result = Vec::<u8>::with_capacity(len as usize);
            let _r = self.seek(SeekFrom::Current(-len));
            let _x =self.read(&mut result);
            result
        }
        else
        {
            Vec::<u8>::new()   
        }
    }

    fn peek_nbytes(&mut self, n :i64) ->Vec<u8>
    {
        let init_position = self.stream_position().unwrap();
        let vec_bytes = self.read_nbytes(n);
        let _r = self.seek(SeekFrom::Start(init_position));
        vec_bytes
    }

    /*iterates backwards in file until next iteration of YAML document sign (---).
            sets the stream offset to the beginning of document.
            returns the position of both ends of said document.
            assumes the current position is before the next document's delimiter*/
    pub fn previous_document_extension(&mut self) -> (u64, u64)
    {
        let delimiter = vec![b'-',b'-',b'-',b'\n'];
        self.move_previous_line();
        let lower_pos = self.stream_position().unwrap();
        let mut upper_pos = lower_pos;

        let mut prev_line_peek = vec![b'0'];
        while prev_line_peek.is_empty()==false && prev_line_peek.eq(&delimiter) ==false
        {
            self.move_previous_line();
            prev_line_peek = self.peek_nbytes(4);
            upper_pos = self.stream_position().unwrap();
        }
        if prev_line_peek.eq(&delimiter) ==true
        {
            let mut _x = String::new();
            let _x =self.read_line(&mut _x);
        }

        (upper_pos,lower_pos-upper_pos)
        
    }

    /*iterates forward until next yaml document delimiter. the extension covers the delimiter for consistency
        with previous_document_extension, the --- will need to be removed during deserialization*/
    pub fn next_document_extension(&mut self) -> (u64,u64)
    {
        let mut next_line = String::from('0');
        let upper_pos = self.stream_position().unwrap();
        let _x =self.read_line(&mut next_line);
        let mut lower_pos = self.stream_position().unwrap();

        while next_line.is_empty()==false && next_line.starts_with("---")==false
        {
            let _x =self.read_line(&mut next_line);
            lower_pos = self.stream_position().unwrap();
        }
        
        (upper_pos,lower_pos-upper_pos)

    }



}

#[pyclass]
pub struct LogManager
{
    reader : YAMLReader,
    writer : BufWriter<File>,
    current_doc_extend : (u64,u64)
}


impl LogManager
{
    /// new(filepath,/)
    /// --
    /// 
    /// builds a new LogManager struct from a given file path
    pub fn new(filepath : &mut String)-> LogManager
    {

        let reader = YAMLReader::new(filepath);

        let path = Path::new(&filepath);
        let bin_file = match File::open(path)
        {
            Err(why) => panic!("couldn't open {} : {}", path.display(), why),
            Ok(file) => file,
        };
        let writer = BufWriter::new(bin_file);
        
        let mut Log  = LogManager{reader:reader,
                                            writer:writer,
                                            current_doc_extend:(0,0)};
        Log.jump_last();
        
        Log
    }
    
    /// byte_jump(byte,/)
    /// --
    /// 
    /// jump to byte positon and attach to the document containing it
    pub fn byte_jump(&mut self,byte : u64)
    {
        let _x = self.reader.seek(SeekFrom::Start(byte));
        self.reader.previous_document_extension(); //move to delimiter
        self.current_doc_extend = self.reader.next_document_extension();
        let _x = self.reader.seek(SeekFrom::Start(self.current_doc_extend.0));
    }

    /// jump_last(/)
    /// --
    /// 
    /// get latest entry
    pub fn jump_last(&mut self)
    {
        let _x = self.reader.seek(SeekFrom::End(0));
        self.current_doc_extend = self.reader.previous_document_extension();
    }
    /// jump_first(/)
    /// --
    /// 
    /// get first entry
    pub fn jump_first(&mut self)
    {
        let _x = self.reader.seek(SeekFrom::Start(0));
        self.current_doc_extend = self.reader.next_document_extension();
    }

    /// peek(/)
    /// --
    /// 
    /// return date and log level from current entry without full deserialization.
    /// assumes the date is ISO YYYY-MM-DD hh:mm:ss:uuuu format and the level <= 9
    pub fn peek(&mut self) ->(String,u8)
    {
        let byte_arr = self.reader.peek_nbytes(41);
        if byte_arr.len()<41
        {
            return (String::from("ERR"),0)
        }
        (String::from_utf8(byte_arr[6..32].to_vec()).unwrap(), byte_arr[40])
    }

    /// move_doc(amount,/)
    /// --
    /// 
    /// move along the documents inside the file. direction is given by the sign of amount.
    pub fn move_doc(&mut self, amount : i32)
    {
        let mut xtend = self.current_doc_extend;
        let sign = amount.signum();
        match sign
        {
            1 => for _i in 0..(amount as usize)
                {
                    xtend = self.reader.next_document_extension();
                },
            -1=> {
                    if self.reader.stream_position().unwrap()==0 {return;} ///case first document
                
                    for _i in 0..(-amount as usize)
                    {
                        xtend = self.reader.previous_document_extension();
                    }
                },
            _=> () //if amount==0 do nothing,
            
        }
        self.current_doc_extend = xtend; //set correct extension
    }

    /// document_string(/)
    /// --
    ///
    //current document as string
    pub fn document_string(&mut self) -> String
    {
        let _x = self.reader.seek(SeekFrom::Start(self.current_doc_extend.0));
        let mut content:String = String::from_utf8(self.reader.read_nbytes(self.current_doc_extend.1 as i64)).unwrap();
        if content.ends_with("---\n")
        {
            content = String::from(&content[..content.len()-4]);
        }

        let _x = self.reader.seek(SeekFrom::Start(self.current_doc_extend.0));
        content

    }

    /// deserialize(/)
    /// --
    ///
    /// return current document as Yaml struct.
    pub fn deserialize(&mut self)->Option<Yaml>
    {
        
        if self.current_doc_extend==(0,0) { return None; }        
        let mut docudict = YamlLoader::load_from_str(&self.document_string()).unwrap();

        Some(docudict[0])
    }

    /// search_date (targ_date,/)
    /// --
    ///
    /// get closest entry to required date, assuming date_string represents an ISO string
    pub fn search_date(&mut self, targ_date : &String)
    {
        
        let mut cur_position = self.reader.stream_position().unwrap();
        let mut soon_bound : u64 = 0;
        let mut late_bound = self.reader.get_len().unwrap();

        let mut cur_date =  String::new();


        let mut dc_stop_condition = false;
        let mut loop_position = self.reader.stream_position().unwrap();
        //byte wise dichotomy to get close to the required entry fast
        while dc_stop_condition==false
        {
            cur_date = self.peek().0;
            cur_position =self.reader.stream_position().unwrap();

            if cur_date == *targ_date {return};
            
            if cur_date > *targ_date
            {
                late_bound = cur_position;
            }
            if cur_date< *targ_date 
            {
                soon_bound = cur_position;
            }

            loop_position = self.reader.stream_position().unwrap();
            self.byte_jump((late_bound+soon_bound)/2);

            if loop_position == cur_position {dc_stop_condition=true;} //stop moving when same document hit twice in a row
        }

        //iterate through documents until
        if cur_date< *targ_date
        {
            while cur_date < *targ_date && cur_date.is_empty()==false
            {
                self.move_doc(1);
                cur_date = self.peek().0;
            }
            self.move_doc(1);
        }

        else {
            
            if cur_date > *targ_date 
            {
                let prev_pos = self.current_doc_extend.0;
                while cur_date> *targ_date && self.reader.stream_position().unwrap()!=0
                {
                    self.move_doc(-1);
                    cur_date = self.peek().0;
                }
                self.move_doc(1);
            }
        }




            


        }

    ///slice_any(up,down,/)
    /// --
    /// 
    /// grab documents in both directions starting from the current one and returns them as a Vec
    pub fn slice(&mut self, up :u32, down : u32) -> Vec<Yaml>
    {
        let start_exten = self.current_doc_extend;
        let mut up_slice = Vec::<Yaml>::new();
        for i in 0..up
        {
            self.move_doc(-1);
            match self.deserialize()
            {
                None => (),
                Some(i) => up_slice.insert(0,i)
            }

        }

        self.reader.seek(SeekFrom::Start(start_exten.0));
        let mut down_slice = Vec::<Yaml>::new();

        match self.deserialize()
        {
            None => (),
            Some(i) => down_slice.push(i)
        }

        for i in 0..down
        {
            self.move_doc(2);
            match self.deserialize()
            {
                None => (),
                Some(i) => down_slice.push(i)
            }
        }

        self.reader.seek(SeekFrom::Start(start_exten.0));
        self.current_doc_extend = start_exten;

        [up_slice,down_slice].concat() 

    }


}





fn main() 
{
    let mut LogLog = LogManager::new(&mut String::from("../../tests/small_log.yaml"));
}
