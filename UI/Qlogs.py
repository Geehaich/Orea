from PyQt6.QtWidgets import QWidget, QHBoxLayout,QVBoxLayout,QScrollBar,QLabel,QPushButton,QSpacerItem
from PyQt6.QtGui import QFontMetricsF
import logic.loglib as loglib


class Dataline(QWidget):

    def __init__(self,content):
        super().__init__()
        self.content = content
        hlay = QHBoxLayout()
        space = QSpacerItem(w = 15)
        hlay.addLayout(space)
        name_label = QLabel(type(content).__name__)
        hlay.addWidget(name_label)

        self.filtered = False

        self.content_label = QLabel()
        self.content_label.setWordWrap(True)
        hlay.addWidget(self.content_label)
        self.set_content_text()

    def set_content_text(self):
        font = QFontMetricsF(self.content_label.font())
        text = str(self.content)
        R = font.boundingRect(str)
        if R.width()> 3* self.content_label.width():
            self.content_label.setText("Hover for value")
            self.content_label.setToolTip(text)
        else:
            self.content_label.setText(text)







class LogWidget(QWidget) :

    def __init__(self,entry : loglib.LogEntry):
        super(LogWidget, self).__init__()
        self.entry_ref = entry

        self.v_lay = QVBoxLayout()
        self.header = QHBoxLayout()
        self.fill_header()
        self.v_lay.addLayout(self.header)


        self.data_lines = []
        self.fill_lines()

    def fill_header(self):

        self.header.addWidget(QPushButton("+"))
        date_label = QLabel(self.entry_ref._date_string)
        self.header.addWidget(date_label)
        level_label = QLabel(self.entry_ref.level.name)
        self.header.addWidget(level_label)
        thread_label = QLabel(self.entry_ref.thread_name)
        self.header.addWidget(thread_label)
        message_label = QLabel(self.entry_ref.thread_name)
        message_label.setWordWrap(True)
        self.header.addWidget(message_label)

    def fill_lines(self):

        for key in self.entry_ref.dict_info :
            D = Dataline(self.entry_ref.dict_info[key])
            self.data_lines.append(D)
            self.v_lay.addWidget(D)

