from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QTextEdit

class ParseFormatDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Parse Format Information")
        self.setMinimumSize(450, 250)
        parse_format_layout = QVBoxLayout(self)
        # 帧结构说明
        group_parse_format = QGroupBox("Serial Parse Format Rules")
        group_layout = QVBoxLayout()
        self.txt_parse_format = QTextEdit()
        self.txt_parse_format.setText(
"""从远端设备发送的数据需要有一定的格式，每行必须以'$'开头，以';'结尾。取值必须以空格分隔。
  例如：$150.0 145.5 2.0 0.5 0.1;
解析程序将根据分隔的字段位置提取目标温度、当前温度和 PID 参数。
""")
        group_layout.addWidget(self.txt_parse_format)
        group_parse_format.setLayout(group_layout)
        parse_format_layout.addWidget(group_parse_format)