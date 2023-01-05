use core::panic;
use std::io::{BufWriter, Seek, SeekFrom, Read};
use std::path::Path;
use std::fs::File;
use rand::Rng;
use pyo3::prelude::*;

use pyo3::types::{PyTuple};
mod reader ;
use reader::{YAMLReader,LogEntry};





#[pyclass]
#[allow(dead_code)]
pub struct LogManager
{
    #[pyo3(get)]
    file_name : String,
    #[pyo3(get)]
    estimated_entry_number : u32,
    reader : YAMLReader,
    writer : BufWriter<File>,//used in python,
    #[pyo3(get,set)]
    current_doc_extend : (u64,u64)
}

#[pymethods]
impl LogManager
{
    /// new(filepath,/)
    /// --
    /// 
    /// builds a new LogManager struct from a given file path
    
    #[new]
    pub fn new(filepath : PyObject)-> PyResult<Self>
    {
        Ok(LogManager::new_from_path(&filepath.to_string()))
    }
    
    /// byte_jump(byte,/)
    /// --
    /// 
    /// jump to byte positon and attach to the document containing it
    pub fn byte_jump(&mut self,byte : u64) -> PyResult<()>
    {
        let _ = self.reader.seek(SeekFrom::Start(byte));
        self.current_doc_extend = self.reader.previous_document_extension(); //move to delimiter
        
        self.current_doc_extend = self.reader.next_document_extension();
        
        let _ = self.reader.seek(SeekFrom::Start(self.current_doc_extend.0));

        Ok(())
    }

    /// file_byte_len
    /// --
    /// 
    /// return length of file in bytes
    pub fn file_byte_len(&mut self) -> PyResult<u64> { Ok(self.reader.get_len().unwrap())}

    /// jump_last(/)
    /// --
    /// 
    /// get latest entry
    pub fn jump_last(&mut self)-> PyResult<()>
    {
        let _ = self.reader.seek(SeekFrom::End(0));
        self.current_doc_extend = self.reader.previous_document_extension();

        Ok(())
    }
    /// jump_first(/)
    /// --
    /// 
    /// get first entry
    pub fn jump_first(&mut self)-> PyResult<()>
    {
        let _ = self.reader.seek(SeekFrom::Start(0));
        self.current_doc_extend = self.reader.next_document_extension();
        let _ = self.reader.seek(SeekFrom::Start(0));
        Ok(())
    }

    /// peek(/)
    /// --
    /// 
    /// return date and log level from current entry without full deserialization.
    /// assumes the date is ISO YYYY-MM-DD hh:mm:ss:uuuu format and the level <= 9
    pub fn peek(&mut self) -> PyResult<(String,u8)>
    {
        let byte_arr = self.reader.peek_nbytes(41);
        if byte_arr.len()<41
        {
            return Ok((String::from("ERR"),0));
        }
        //log levels are in  0-9 range, so 48-57 in ASCII table
        Ok((String::from_utf8(byte_arr[6..32].to_vec()).unwrap(), byte_arr[40] - 48 ))
    }

    /// move_doc(amount,/)
    /// --
    /// 
    /// move along the documents inside the file. direction is given by the sign of amount.
    pub fn move_doc(&mut self, amount : i32) -> PyResult<()>
    {
        let mut xtend = self.current_doc_extend;
        let sign = amount.signum();
        match sign
        {
            1 => {
                    for _i in 0..(amount+1) as usize 
                    {
                        
                        xtend = self.reader.next_document_extension();
                    }
                    let _ = self.reader.seek(SeekFrom::Start(xtend.0)); //next document extension places the cursor at the end of the document, put it back at beginning
                },
            -1=> {
                    if self.reader.stream_position().unwrap()==0 {return Ok(());} //case first document
                    
                    for _i in 0..-amount as usize
                    {
                        if self.current_doc_extend.0 !=0 { xtend = self.reader.previous_document_extension();}
                    }

                    
                    
                },
            _=> () //if amount==0 do nothing,
            
        }
        self.current_doc_extend = xtend; //set correct extension
        Ok(())
    }



    /// search_date (targ_date,/)
    /// --
    ///
    /// get closest entry before required date, assuming date_string represents an ISO string
    pub fn search_date(&mut self, py_targ_date : PyObject) ->PyResult<()>
    {
        let targ_date = py_targ_date.to_string();        
        let mut cur_position ;
        let mut soon_bound : u64 = 0;
        let mut late_bound = self.reader.get_len().unwrap();
        let mut cur_date : String = String::new();

        let mut dc_stop_condition = false;
        let mut loop_position ;
        //byte wise dichotomy to get close to the required entry fast
        while dc_stop_condition==false
        {
            cur_date = self.peek().unwrap().0;
            cur_position =self.reader.stream_position().unwrap();

            if cur_date == targ_date {return Ok(())};
            
            if cur_date > targ_date
            {
                late_bound = cur_position;
            }
            if cur_date< targ_date 
            {
                soon_bound = cur_position;
            }

            
            let _ = self.byte_jump((late_bound+soon_bound)/2);
            loop_position = self.reader.stream_position().unwrap();

            if loop_position == cur_position {dc_stop_condition=true;} //stop moving when same document hit twice in a row
        }

        //iterate through documents until
        if cur_date < targ_date
        {
            let _prev_pos = self.current_doc_extend.0;
            while cur_date < targ_date && cur_date.is_empty()==false
            {
                let _ =self.move_doc(1);
                cur_date = self.peek().unwrap().0;
                if cur_date==targ_date {return Ok(());}
            }
            let _ = self.move_doc(-1);
        }

        else {
            
            if cur_date > targ_date 
            {
                
                while cur_date> targ_date && self.reader.stream_position().unwrap()!=0
                {
                    let _ =self.move_doc(-1);
                    cur_date = self.peek().unwrap().0;
                    if cur_date==targ_date {return Ok(());}
                }
                
            }
            let _ = self.move_doc(1);
        }

        Ok(())




            


        }

    ///move_until(direction,condition_func,/)
    /// --
    /// 
    /// move in the file from current document until a condition on the entry is met.
    /// direction is given by the sign of the direction argument : if >0, goes down, else up.
    /// Unlike most other functions, doesn't move the cursor back to where it was before function call.
    pub fn move_until(&mut self, direction : i8 ,condition_func : PyObject) -> PyResult<Option<LogEntry>>
    {
        let gil = Python::acquire_gil();
        let py = gil.python();
        let increment = direction.signum();
        if increment == 0 || condition_func.is_none(py) {return Ok(None);} // case of invalid arguments

        while self.current_doc_extend.0!=0 && self.current_doc_extend.1!=0
        {
            let entry_option =self.current_entry().unwrap();
            match  entry_option
            {
                None => return Ok(None),
                Some(entry) =>
                {
                        let entry_pytuple = PyTuple::new(py, &[entry.clone().into_py(py)]);
                        let cond_result : bool= condition_func.call1(py,entry_pytuple)?.extract(py)?;
                        if cond_result == true
                        {
                            return Ok(Some(entry));
                        }
                    }

            }

        }

        Ok(None)
    


    }

    ///slice_conditional(up,down,condition_func/)
    /// --
    /// 
    /// grab entries in both directions starting from the current one for which condition_func(entry) is True and returns them as a Vec.
    pub fn slice_conditional(&mut self, up :u32, down : u32,
         condition_func : PyObject) -> PyResult<Vec<LogEntry>>
    {

        let gil = Python::acquire_gil();
        let py = gil.python();

        let start_xten = self.current_doc_extend;
        let mut up_slice = Vec::<LogEntry>::new();
        for _i in 0..up
        {
            let _ = self.move_doc(-1);
            let entry_option =self.current_entry().unwrap();
            match  entry_option
            {
                None => (),
                Some(entry) =>
                {
                    if condition_func.is_none(py) == false
                    {
                        
                        let entry_pytuple = PyTuple::new(py, &[entry.clone().into_py(py)]);
                        let cond_result : bool= condition_func.call1(py,entry_pytuple)?.extract(py)?;
                        if cond_result == true
                        {
                            up_slice.push(entry.clone());
                        }
                    }

                    else
                    {
                        up_slice.push(entry.clone());
                    }

                    if self.current_doc_extend.0 == 0 //stop iterating if first document reached
                    {
                        break;
                    }
                }
            }
            
        }

        self.set_xten(start_xten); //back to initial

        let mut down_slice = Vec::<LogEntry>::new();

        for _i in 0..down
        {
            //put current doc in the down part of the slice by only moving after first pass
            if _i >0{ let _ =self.move_doc(1); }
            let entry_option =self.current_entry().unwrap();
            match  entry_option
            {
                None => (),
                Some(entry) =>
                {
                    if condition_func.is_none(py) == false
                    {
                    let entry_pytuple = PyTuple::new(py, &[(entry).clone().into_py(py)]);
                        let cond_result : bool= condition_func.call1(py,entry_pytuple)?.extract(py)?;
                        if cond_result == true
                        {
                            down_slice.push(entry.clone());
                        }
                    }

                    else
                    {
                        down_slice.push(entry.clone());
                    }


                    //after last document reached, move() will set current extension to (last_byte,0).
                    //in this case we remove the last entry and stop iteration
                    if self.current_doc_extend.1 ==0 
                    {
                        let _ = down_slice.pop(); 
                        break;
                    }
                }
            }
        }

        self.set_xten(start_xten);

        Ok([up_slice,down_slice].concat() )

    }

    ///entry_size_estimate
    /// --
    /// 
    /// randomly access 50 entries, returns their mean size in bytes and stores it in the mean_size_estimate field.
    pub fn entry_size_estimate(&mut self) -> PyResult<u32>
    {
        let start_xten = self.current_doc_extend;
        let maxbyte = self.reader.get_len().unwrap();
        let mut total_bytes = 0;
        
        let mut rng = rand::thread_rng();
        for _i in 0..50
        {
            let _ = self.byte_jump(rng.gen_range(0..maxbyte));
            total_bytes += self.current_doc_extend.1;
        }

        self.set_xten(start_xten);
        self.estimated_entry_number =  (maxbyte / (total_bytes /50) )as u32;
        Ok(self.estimated_entry_number)


    }

    
    /// date_interval(date1, date2,cond_func/)
    /// --
    /// 
    /// get documents between two dates according to condition. Puts cursor back in initial position.
    /// NOTA : based on search_date function, does not return the closest entry to either date but the first with date <= to it
    pub fn date_interval(&mut self, date1 : PyObject , date2 : PyObject , cond_func : PyObject) -> PyResult<Vec<LogEntry>>
        {

        let gil = Python::acquire_gil();
        let py = gil.python();

        let  d1_str = date1.to_string();
        let  d2_str = date2.to_string();

        let second_date : String;


        let initial_doc_xten = self.current_doc_extend;
        if d1_str < d2_str //move to oldest document, store latest date as stop conditoin
        {
            let _ = self.search_date(date1);
            second_date = d2_str;
        }   
        else
        {
            let _ = self.search_date(date2);
            second_date = d1_str;
        }


        let mut res_vec = Vec::<LogEntry>::with_capacity(16);
        //go down the file and push every entry until second date reached or EoF
        while self.current_doc_extend.1 !=0
        {
            let entry_option =self.current_entry().unwrap();
            match  entry_option
            {
                None => (),
                Some(entry) =>
                {
                    if cond_func.is_none(py) == false
                    {
                        let entry_pytuple = PyTuple::new(py, &[entry.clone().into_py(py)]);
                        let peek_result : bool= cond_func.call1(py,entry_pytuple)?.extract(py)?;
                        if peek_result == true { res_vec.push(entry.clone());}
                    }
                    else 
                    {
                        res_vec.push(entry.clone());            
                    }
                    let _= self.move_doc(1);
        
                    if self.peek().unwrap().0 > second_date {break;}
                }
            }
            
        }


        self.set_xten(initial_doc_xten);
        Ok(res_vec)

    }


    fn __repr__(&mut self)-> PyResult<String>
    {
        let rep  = format!("LogManager bound to {} :\ncurrent position {}\nfile byte size {} \nest. number of entries {}",
         self.file_name,self.reader.stream_position().unwrap(),
        self.reader.get_len().unwrap(),self.estimated_entry_number as u64+1);

        Ok(rep)
    }



    /// current_entry
    /// --
    /// 
    /// build LogEntry out of current document
    pub fn current_entry(&mut self) ->PyResult<Option<LogEntry> >
    {
        if self.current_doc_extend.1 ==0 { Ok(None) }
        else { Ok(LogEntry::get_entry(self)) }
        
    } 


    ///get_content(entry,/)
    /// --
    /// 
    /// get optional fields of a LogEntry as a string. YAML deserialization should be handled python-side to allow more genericity.
    pub fn get_content(&mut self, entry : LogEntry) -> PyResult<String>
    {
        if entry.dic_extension.1==0
        {
            return Ok("".to_string());
        }
        let start_xten = self.current_doc_extend;
        let mut result = Vec::<u8>::with_capacity(entry.dic_extension.1 as usize);
            unsafe {result.set_len(entry.dic_extension.1  as usize);}
        let _ = self.reader.seek(SeekFrom::Start(entry.dic_extension.0));
        let _= self.reader.read(&mut result);

        if result.ends_with(&[b'\n',b'-',b'-',b'-',b'\n']) {result.resize(result.len()-5,b'\0');} //extension covers the end of document line in YAML, remove it for deserialization

        self.set_xten(start_xten);
        Ok(String::from_utf8_lossy(&result).to_string())
    }

}

impl LogManager //Rust funcs
{
        /// document_string(/)
    /// --
    ///
    //current document as string
    pub fn document_string(&mut self) -> String
    {
        let _ = self.reader.seek(SeekFrom::Start(self.current_doc_extend.0));
        let mut content:String = String::from_utf8(self.reader.read_nbytes(self.current_doc_extend.1 as i64)).unwrap();
        if content.ends_with("---\n")
        {
            content = String::from(&content[..content.len()-4]);
        }

        let _ = self.reader.seek(SeekFrom::Start(self.current_doc_extend.0));
        content

    }

    pub fn new_from_path(filepath :&str) -> LogManager
    {
        let mut filestring = filepath.to_string();
        let reader = YAMLReader::new(&mut filestring);

        let path = Path::new(&mut filestring);
        let bin_file = match File::open(path)
        {
            Err(why) => panic!("couldn't open {} : {}", path.display(), why),
            Ok(file) => file,
        };
        let writer = BufWriter::new(bin_file);
        
        let mut log  = LogManager{file_name:filestring,
                                             reader:reader,
                                             estimated_entry_number : 0,
                                             writer:writer,
                                            current_doc_extend:(0,0)};
                                            
        let _ = log.jump_last();
        if log.reader.get_len().unwrap()!=0 
        {
            let _ = log.entry_size_estimate();
        }
        
        log
    }

    fn set_xten(&mut self,xten :(u64,u64)) //set extension from tuple and go to first item. subfunc, used a lot in others
    {
        self.current_doc_extend = xten;
        let _ = self.reader.seek(SeekFrom::Start(xten.0));
    }

    

}



#[pymodule]
fn orea_core(_py:Python, m :&PyModule) -> PyResult<()>
{
    m.add_class::<LogEntry>()?;
    m.add_class::<LogManager>()?;
    Ok(())
}

#[test]
fn test_fun()
    {
            let mut Lm = LogManager::new_from_path("/home/guillaume/repos/Orea/tests/empty.yaml");
            println!("{:?}",Lm.current_doc_extend);
    }

