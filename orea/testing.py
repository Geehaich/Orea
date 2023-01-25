from orea.logcontroller import LogController
from orea.loglib import LogManagerWrapper
import os

import rich
from orea.loglib import LogManagerWrapper


fpath = os.path.abspath('../tests/moby/moby0.yaml')

con = LogController([fpath])
ent = con.log_mans[fpath].current_entry()
pret = con.prettify_entry(ent)
print(pret)
