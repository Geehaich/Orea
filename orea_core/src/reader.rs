use core::panic;
use std::io::{BufReader, Seek, SeekFrom, Read, BufRead,Result};
use std::path::Path;
use std::fs::File;
use pyo3::prelude::*;
use pyo3::basic::CompareOp;
use pyo3::exceptions::PySyntaxError;
use crate::LogManager;

// static strings corresponding to first mandatory field names in YAML docs

use crate::globals::{DOC_DELIMITER,CLASSIC_LOG_LEVELS,DOC_FIELD_DATE,DOC_FIELD_TOPIC, SPLIT_DELIMITER_BYTES};

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
    pub fn read_nbytes(&mut self,n : i64) -> Vec<u8>
    {
        let cur_pos = self.stream_position().unwrap();
        let max_pos = self.get_len().unwrap();
        
        if n>0
        {
            let len = ((max_pos-cur_pos) as i64).min(n);
            let mut result = Vec::<u8>::with_capacity(len as usize);
            unsafe {result.set_len(len as usize);}
            let _x = self.read(&mut result);
            return result
        }
        else if n<0
        {
            let len = 0.max(cur_pos as i64 +n);
            let mut result = Vec::<u8>::with_capacity(len as usize);
            unsafe {result.set_len(len as usize);}
            let _r = self.seek(SeekFrom::Current(-len));
            let _x =self.read(&mut result);
            return result
        }
        else
        {
            return Vec::<u8>::new()   
        }
    }

    pub fn peek_nbytes(&mut self, n :i64) ->Vec<u8>
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
        
        if self.peek_nbytes(4).eq(&SPLIT_DELIMITER_BYTES)==false { self.move_previous_line();}
        let lower_pos = self.stream_position().unwrap();
        let mut upper_pos = lower_pos;

        let mut prev_line_peek = vec![b'0'];
        while upper_pos!=0 && prev_line_peek.is_empty()==false && prev_line_peek.eq(&SPLIT_DELIMITER_BYTES) ==false
        {
            self.move_previous_line();
            prev_line_peek = self.peek_nbytes(4);
            upper_pos = self.stream_position().unwrap();
        }
        if prev_line_peek.eq(&SPLIT_DELIMITER_BYTES) ==true
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

        while next_line.is_empty()==false && next_line.starts_with(DOC_DELIMITER)==false
        {
            next_line.clear();
            let _x =self.read_line(&mut next_line);
            lower_pos = self.stream_position().unwrap();
        }
        let mut true_lowest = lower_pos-upper_pos;
        if true_lowest > 4 {true_lowest -=4;}
        (upper_pos,true_lowest)

    }




}


#[pyclass]
#[derive(Clone)]
#[allow(dead_code)] //POD struct for python, unread here
pub struct LogEntryCore //represents a log entry with accessible usual fields and the byte location of optional data
{
    #[pyo3(get)]
    pub date : String,
    #[pyo3(get)]
    pub level: u8,
    #[pyo3(get)]
    pub message : String,
    #[pyo3(get)]
    pub topic : String,
    #[pyo3(get)]
    pub dic_extension : (u64,u64),
    #[pyo3(get)]
    pub total_extension : (u64,u64),
}

#[pymethods]
impl LogEntryCore
{
    fn __repr__(&mut self)-> PyResult<String> //quick representation for console
    {
        let mut rep =self.date[..self.date.len()-3].to_string();
        rep.push_str(" | ");

        if (self.level as usize) < CLASSIC_LOG_LEVELS.len() { rep.push_str(format!("{} | ",CLASSIC_LOG_LEVELS[self.level as usize]).as_str());}
        else { rep.push_str(format!("{} | ",self.level).as_str());}

        let maxline = 50;
        if self.message.char_indices().count()<=maxline { rep.push_str(format!("{} | {} | ",self.topic, self.message).as_str());}
        else {rep.push_str(format!("{} | {}... | ",self.topic, &self.message[..self.message.char_indices().nth(maxline).unwrap().0]).as_str())};
        if self.dic_extension.1 != 0 { rep.push_str(" + YAML ");}

        Ok(rep)
    }
    
    fn is_equal(&self, other : &LogEntryCore) ->bool
    {
        self.date == other.date 
            && self.level == other.level
            && self.topic == other.topic
            && self.message == other.message
    }

    fn __richcmp__(&self, other: &Self, op: CompareOp) -> PyResult<bool> {
        match op {
            CompareOp::Eq => Ok(self.is_equal(other)),
            CompareOp::Ne => Ok(!self.is_equal(other)),
            _=> Err(PyErr::new::<PySyntaxError, _>("only == and != operators are implemented for LogEntryCore."))
        }
    }

}

impl LogEntryCore
{   

    pub fn get_entry(lm : &mut LogManager) ->Option<LogEntryCore> //build entry struct from current document the logmanager points to
    {
        let xten = lm.current_doc_extend;

        let mut str_date = String::new();
        let mut str_lev = String::new();
        let mut str_topic = String::new();
        let mut str_mes = String::new();

        let _ = lm.reader.read_line(&mut str_date);
        if str_date.starts_with(DOC_DELIMITER) 
        {
            str_date.clear();
            let _= lm.reader.read_line(&mut str_date);
            if str_date.len()<6 {return None;} //case EoF
        } //depending on direction of search, document may begin at either side of delimiter
        let _ = lm.reader.read_line(&mut str_lev);
        let _ = lm.reader.read_line(&mut str_topic);

        let str_lev = str_lev.as_str(); //level is numeric in 0-99 range
        let lev = str::parse::<u8>(&str_lev[(str_lev.len()-2)..].trim());
        let n_lev;
        match lev
        {
            Ok(_l) => { n_lev = lev.unwrap();},
            Err(_l) => { n_lev = 99 as u8;}
        }

        str_date = str_date[DOC_FIELD_DATE.len()..].trim().to_string(); // line starts with "date: "
        str_topic = str_topic[DOC_FIELD_TOPIC.len()..].trim().to_string(); //"topic: "

        let _ = lm.reader.read_line(&mut str_mes); //first line of mandatory message field
        let mut start_char = lm.reader.peek_nbytes(1); //read first char of each line until not whitespace (next entry field)
        while start_char.len()!=0 && start_char[0]==b' '
        {
            let _ = lm.reader.read_line(&mut str_mes);
            start_char = lm.reader.peek_nbytes(1);
        }

        str_mes = str_mes.splitn(2,": ").nth(1).unwrap().trim_end().to_string();
        let str_mes = String::from(str_mes.as_str());

        let pos = lm.reader.stream_position().unwrap();
        let mut dic_xten : u64  =0;
        if xten.0+xten.1 > pos {dic_xten = xten.0+xten.1-pos;}


        //set cursor back to start
        lm.set_xten(xten);

        Some(LogEntryCore
         {
            date:str_date,
            level :n_lev,
            topic: str_topic,
            message : str_mes,
            dic_extension : (pos, dic_xten),
            total_extension : xten
         })
    }

}
