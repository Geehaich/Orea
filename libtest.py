import loglib as ll
import orea_core
import time
import CLI.Terminal_funcs as tfunc
from rich.console import Console


console = Console(color_system="256")
Lm = ll.LogManagerWrapper("/home/guillaume/repos/Orea/tests/test.yaml")
tfunc.pretty_print_entry(Lm.current_entry())
Lm.move(-60)
Lm.slice_up(15)
for entry in Lm.queue:
    tfunc.pretty_print_entry(entry)


