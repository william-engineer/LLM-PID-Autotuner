from PyQt5.QtWidgets import QGroupBox, QStyleOptionGroupBox, QStyle
from PyQt5.QtCore import pyqtSignal

class DoubleClickTitleGroupBox(QGroupBox):
    titleDoubleClicked = pyqtSignal()

    def mouseDoubleClickEvent(self, event):
        # 通过 QStyleOptionGroupBox 获取标题区域的矩形，并判断双击位置是否在标题区域内
        opt = QStyleOptionGroupBox()
        self.initStyleOption(opt)
        title_rect = self.style().subControlRect(
            QStyle.CC_GroupBox, opt, QStyle.SC_GroupBoxLabel, self
        )
        if title_rect.contains(event.pos()):
            self.titleDoubleClicked.emit()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)