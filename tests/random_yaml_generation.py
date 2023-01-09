import string
import sys
from collections import OrderedDict
import yaml
from datetime import datetime
import numpy as np
letters = np.array(list(string.ascii_uppercase+string.ascii_lowercase+" "*16+"""是指利用水资源结合沐浴、按摩、塗抹保養品和香熏来促进新陈代谢，满足人体视觉、味觉、触觉、嗅觉和思考达到一种身心畅快的享受。目前spa業界的说法认为，spa是由专业美疗师、水、光线、芳香精油、音乐等多个元素组合而成的舒缓减压方式，能帮助人达到身、心、灵的健美，所以高級的spa館通常都設在風景宜人的度假村，以尋求安寧的環境和清新空氣，而考慮到經營模式所以都和大飯店為複合方式並存，成為休假旅行的活動行程之一以吸引顧客。
spa这种休闲美容方式的历史很久远。在15世纪欧洲的比利时有一个被称之为spau的小山谷（即今日的斯帕地區），山谷中有一个富含矿物质的热温泉旅游、疗养区，当时有许多贵族到这里来度假疗养这就是spa最初的形式。18世纪后开始在欧洲贵族中风行開來，成为贵族们休闲度假、强身健体的首选，20世纪末在欧美民間社會又重新掀起了spa热潮，并于21世纪初传入亞洲各國t̴̞̔e̴̪̎r̸̲̔ś̵̳h̵͚͑'̷̮̏ẹ̴̀-̸̩͋u̶̱̔e̶͓̾r̸̝̂y̷̙͝"̴͖̉j̵̯̓ḧ̵͓́ ̴͎̌h̵̡̀ ̸͚̾t̸̳͌r̵̮͛s̵̰͆t̷͕͛r̷̤̔z̵͉̀s̴̻̚h̷̫͌z̷̯͋ŗ̶̃u̷̬̿y̸͕̎h̷̟̓-̸̯̓ë̷͖j̵̤̀-̶̙̿(̵̮̋e̸̮͑V̴͙̀'̵̪̇Z̸̛̰A̸̱͗"̷̱̀É̸̥̈́F̵͜͠Z̷̮͌F̶̦̍'̵̦̈"̷̞̒Â̵͓G̵͉͑(̸̿ͅE̵̖̍Ă̶̼(̶̬͛T̸͔̎(̴̗̂"̸̩͝Å̶ͅG̷̒͜T̵̜͊'̶̙̃Ẓ̷͋Q̷̛̟G̸͊ͅ(̸̫̉'̷̢̓"̴̬̇Z̵̲̒H̷̡̊T̷̢̀X̴͍͌W̴͙͝Ġ̵̖Ẽ̵̙S̵̨͝_̷͜͝u̵̟͑-̷̥͛(̴̠͋i̶̻͝d̴̠̊g̸̪͐'̵͙̅"̶̗͝&̵͓͋g̴͎̊f̶͍͛v̵̩̋e̴̘͂ȓ̴͎s̷̙͆q̷͍̓b̸̨͑v̶͚̾f̵͓͌r̴̮͝s̸̤͘q̷͕͆g̶͙̀(̶̛̞ȩ̷͗s̵̻̉y̶̧͌ĥ̵̙(̷̰̒e̷̞̾u̸̟͠y̷̯͘-̵̛̳(̸̊ͅ'̵̯̅y̵̘͋ë̷̠́s̴̪̋q̶̳̑f̸͈͘é̴͖̌z̴̭̅B̴͍̊Z̵͇͗ ̸̞̾Q̵͕̒ ̷̼̀G̷̟͐R̴̪͒Q̸̉͜ ̸̆͜G̸̪̑E̴͓̾R̵͖͌Q̶͖̔Ġ̷̘8̴̳̾7̵̨͑Ę̵̕Q̷̨̿9̴͓̽7̸̙̀9̶̞̑5̸͉̚4̸̥͘1̶͝ͅ5̵̠̒6̶̟̈́4̴̖͊0̴̫͝"""))

#generate a file containing random entries for testing purposes

def random_entry() :
    date = datetime.now()
    topic = np.random.randint(0,55)
    level = np.random.randint(0,5)
    message  = ''.join(np.random.choice(letters) for i in range(np.random.randint(20,580)))
    or_dict = OrderedDict({"date":date,"level":level,"topic":topic,"message":message})
    if np.random.randint(1,100) >85 :
        or_dict["MAT"] = np.random.randn(np.random.randint(3,11),np.random.randint(3,5))
        if np.random.randint(1,100)>50:
            or_dict["VEC"] = np.random.randn(1,7)
    if np.random.randint(1,100) >15 :
        or_dict["ENUM"] = "OPTION_A" if np.random.random()>0.5 else "OPTION_B"
    return dict(or_dict)

if __name__=="__main__":
    
    file_p = open(sys.argv[2] if len(sys.argv)>=3 else 'test.yaml',"w")
    maxi = int(sys.argv[1])

    for i in range(maxi):
        yaml.dump_all([random_entry() for j in range(10)],file_p,sort_keys=False,allow_unicode=True)
        print("{0}    random entries generated in ./test.yaml \r".format(i*10),end="")
        file_p.write("\n---\n")
    file_p.close()
