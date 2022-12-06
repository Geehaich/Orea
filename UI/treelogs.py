from PySide6.QtWidgets import QApplication, QLabel, QTreeView, QTreeWidget,QTreeWidgetItem
import sys

data = {"Project A": ["file_a.py", "file_a.txt", "something.xls"],
        "Project B": ["file_b.csv", """Lorsque avec ses enfants vêtus de peaux de bêtes,
Echevelé, livide au milieu des tempêtes,
Caïn se fut enfui de devant Jéhovah,
Comme le soir tombait, l'homme sombre arriva
Au bas d'une montagne en une grande plaine ;
Sa femme fatiguée et ses fils hors d'haleine
Lui dirent : « Couchons-nous sur la terre, et dormons. »
Caïn, ne dormant pas, songeait au pied des monts.
Ayant levé la tête, au fond des cieux funèbres,
Il vit un oeil, tout grand ouvert dans les ténèbres,
Et qui le regardait dans l'ombre fixement."""],
        "Project C": []}
app = QApplication(2)
tree = QTreeWidget()
tree.setHeaderLabels(["Name", "Type"])
items = []
for key, values in data.items():
    item = QTreeWidgetItem([key])
    for value in values:
        ext = value.split(".")[-1].upper()
        child = QTreeWidgetItem([value, ext])
        child.setToolTip(0,value)
        item.addChild(child)
    items.append(item)

tree.insertTopLevelItems(0, items)
tree.show()
sys.exit(app._exec())