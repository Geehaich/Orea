import string

import yaml
from datetime import datetime
import numpy as np
letters = np.array(list(string.ascii_uppercase+string.ascii_lowercase+" "*16))

#generate a file containing random entries for testing purposes

def random_entry() :
    date = datetime.now()
    thread = np.random.randint(0,55)
    level = np.random.randint(0,5)
    message  = ''.join(np.random.choice(letters) for i in range(np.random.randint(20,580)))
    optional_dict = {}
    if np.random.randint(1,100) >85 :
        optional_dict["a"] = np.random.randn(3,3)
        if np.random.randint(1,100)>50:
            optional_dict["b"] = np.random.randn(1,7)
    return {"date":date,"level":level,"thread":thread,"message":message,"optional_dict":optional_dict}

if __name__=="__main__":
    
    file_p = open("./test.yaml","w")

    for i in range(30000) :
        yaml.dump_all([random_entry()for j in range(50)],file_p)
        print(i)
        file_p.write("\n---\n")
    file_p.close()