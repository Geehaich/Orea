
//recurring static variables


pub static SPLIT_DELIMITER_BYTES_ENDL : [u8;5] = [b'\n',b'-',b'-',b'-',b'\n'];
pub static SPLIT_DELIMITER_BYTES : [u8;4] = [b'-',b'-',b'-',b'\n'];

// static strings corresponding to first mandatory field names in YAML docs
pub static DOC_FIELD_DATE: &str = "date: ";
pub static DOC_FIELD_TOPIC: &str = "topic: ";
pub static DOC_DELIMITER : &str = "---";

pub static CLASSIC_LOG_LEVELS : &'static [&'static str]= &["FATAL","ERROR","WARN","INFO","DEBUG","TRACE"];
