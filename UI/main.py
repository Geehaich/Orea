import sys

from PyQt6.QtWidgets import QWidget,QSpacerItem, QTreeWidget,QTreeWidgetItem, QApplication
from PyQt6.QtGui import QFontMetricsF
import logic.loglib as loglib

class LogTopNode(QTreeWidgetItem) :

    def __init__(self,entry : loglib.LogEntry ):

        self.log_ref = entry
        super().__init__([entry.date_string,loglib.log_levels[entry.level],entry.thread_name,entry.message])
        self.header = QTreeWidgetItem(["name","type","value"])
        self.addChild(self.header)
        self.nodes = LogDictNode(entry.dict_info)
        self.addChild(self.nodes)

class LogDictNode(QTreeWidgetItem) :

    def __init__(self,data_dict):
        super().__init__()
        for key in data_dict :
            if type(data_dict[key])==dict :
                child = LogDictNode(data_dict[key])
                self.addChild(child)
            else :
                value_string = str(data_dict[key])
                child = None
                if len(value_string)>400:
                    child = QTreeWidgetItem([key,type(key).__name__,"###"])
                    child.setToolTip(2,value_string)
                    child.setSizeHint(2,(150,300))
                else:
                    child = QTreeWidgetItem([key,type(key).__name__,value_string])
                self.addChild(child)



if __name__=="__main__":
    Lm = loglib.LogManager('../tests/test.yaml')
    app = QApplication(sys.argv)
    tree = QTreeWidget()
    tree.setHeaderLabels(["Date", "Level","Thread","Message"])

    items = [LogTopNode(entry) for entry in Lm.logs]
    tree.insertTopLevelItems(0, items)
    tree.show()
    app.exec()