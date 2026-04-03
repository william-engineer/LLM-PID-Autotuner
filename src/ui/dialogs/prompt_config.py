from datetime import datetime
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QTextEdit, QHBoxLayout, QPushButton
import os
from config.settings import SYSTEM_DEFAULT_PROMPT


class PromptConfigDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Prompt Configuration")
        self.setMinimumSize(500, 550)
        self.parent_app = parent
        
        # 继承主窗口的暗黑风格
        self.setStyleSheet(parent.styleSheet() + """
            QDialog { background-color: #0b0f19; }
            QCheckBox { color: #00ffcc; }
            QScrollArea { border: none; background-color: transparent; }
            QScrollArea > QWidget > QWidget { background-color: transparent; }
        """)

        prompt_config_layout = QVBoxLayout(self)

        # 提示词设置
        group_prompt = QGroupBox("System Prompt Settings")
        prompt_setting_layout = QVBoxLayout()
        self.txt_prompt = QTextEdit()
        self.txt_prompt.setText(self.parent_app.current_prompt)
        prompt_setting_layout.addWidget(self.txt_prompt)
        group_prompt.setLayout(prompt_setting_layout)
        prompt_config_layout.addWidget(group_prompt)

        # 底部按钮
        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("APPLY && SAVE")
        btn_apply.clicked.connect(self.apply_and_save_prompt)
        btn_default = QPushButton("DEFAULT PROMPT")
        btn_default.clicked.connect(self.back_to_default_prompt)
        btn_layout.addWidget(btn_apply)
        btn_layout.addWidget(btn_default)
        prompt_config_layout.addLayout(btn_layout)

    def apply_and_save_prompt(self):
        new_prompt = self.txt_prompt.toPlainText()
        self.parent_app.current_prompt = new_prompt
        # 新建一个文件来保存当前提示词，文件格式为纯文本，命名为 时间_prompt.txt，保存在当前脚本所在目录
        os.makedirs("prompt", exist_ok=True)
        with open(f"prompt/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}_prompt.txt", "w") as f:
            f.write(new_prompt)
        self.accept()

    def back_to_default_prompt(self):
        self.parent_app.current_prompt = SYSTEM_DEFAULT_PROMPT
        self.txt_prompt.setText(SYSTEM_DEFAULT_PROMPT)