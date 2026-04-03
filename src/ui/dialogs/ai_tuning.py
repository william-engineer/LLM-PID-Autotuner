from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGroupBox, QTextEdit, QHBoxLayout, QLabel, QLineEdit, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from core.llm_client import LLMTuner
from core.tuner_state import TuningHistoryManager
from threads.api_thread import APITestThread
from threads.tuning_thread import AITuningThread

class AITuningDialog(QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setStyleSheet(parent.styleSheet() + """
            QDialog {
                background-color: #0b0f19; 
            }
            QGroupBox {
                border: 1px solid #1a2a3a;
                border-radius: 5px;
                margin-top: 15px;
                font-family: 'Consolas', monospace;
                font-weight: bold;
                font-size: 16pt;           
                color: #00ffcc; 
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center; 
                padding: 0 10px;
            }
            QTextEdit {
                background-color: #000000; 
                border: 1px solid #1a2a3a;
                color: #00e5ff;
                font-family: 'Consolas', monospace;
                font-size: 13pt;
                padding: 5px;
            }
            QScrollBar:vertical {
                border: none;
                background: #0b0f19;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: #1a2a3a;
                min-height: 20px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical:hover { background: #00ffcc; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QPushButton {
                background-color: transparent;
                border-radius: 4px;
                padding: 8px 15px;
                font-family: 'Consolas', monospace;
                font-weight: bold;
                font-size: 13pt;
            }
            QPushButton#btn_start {
                border: 1px solid #00ffcc; 
                color: #00ffcc;
            }
            QPushButton#btn_start:hover { background-color: rgba(0, 255, 204, 0.15); }
            QPushButton#btn_start:pressed { background-color: #00ffcc; color: #0b0f19; }
            QPushButton#btn_api_test {
                border: 1px solid #ffb300; 
                color: #ffb300;
            }
            QPushButton#btn_api_test:hover { background-color: rgba(255, 179, 0, 0.15); }
            QPushButton#btn_api_test:pressed { background-color: #ffb300; color: #0b0f19; }
            QPushButton#btn_stop {
                border: 1px solid #ff4444;
                color: #ff4444;
            }
            QPushButton#btn_stop:hover { background-color: rgba(255, 68, 68, 0.15); }
            QPushButton#btn_stop:pressed { background-color: #ff4444; color: #0b0f19; }
        """)
        self.setWindowTitle("AI Tuning In Progress")
        self.setBaseSize(700, 800)
        # 窗口居中显示
        parent_rect = parent.frameGeometry()
        center_point = parent_rect.center()
        dialog_rect = self.frameGeometry()
        dialog_rect.moveCenter(center_point)
        self.move(dialog_rect.topLeft())
        self.parent_app = parent

        # 整定属性
        self.tuning_thread = None
        self.tuner = LLMTuner(api_key=self.parent_app.le_api_key.text(), base_url=self.parent_app.le_base_url.text(), model=self.parent_app.cb_model.currentText(), provider=self.parent_app.le_provider.text())
        self.history = TuningHistoryManager(max_history=5)
        self.api_test_thread = None

        tuning_layout = QVBoxLayout(self)

        # AI 对话框
        group_ai_analysis = QGroupBox("AI Analysis")
        ai_analysis_layout = QVBoxLayout()
        self.txt_ai_console = QTextEdit()
        ai_analysis_layout.addWidget(self.txt_ai_console)


        # PID状态
        pid_layout = QHBoxLayout()
        lbl_pid_title = QLabel("LLM PID STATUS")
        # lbl_pid_title.setAlignment(Qt.AlignLeft)
        lbl_pid_title.setStyleSheet("""
            QLabel {
                color: #6699bb;
                font-weight: bold; 
                margin-top: 15px; 
                margin-bottom: 5px; 
                padding-top: 10px;  
                border-top: 1px solid #1a2a3a;
            }
        """)
        ai_analysis_layout.addWidget(lbl_pid_title)

        # 上一次 PID (Prev PID)
        self.le_prev_pid = QLineEdit(f"Kp: --- | Ki: --- | Kd: ---")
        self.le_prev_pid.setReadOnly(True)
        self.le_prev_pid.setAlignment(Qt.AlignCenter)
        self.le_prev_pid.setStyleSheet("""
            QLineEdit {
                background-color: #1a1a24; 
                color: #888888; 
                border: 1px dashed #334455;
            }
        """)
        row_prev_layout = QHBoxLayout()
        prev_lbl = QLabel("Prev PID"); prev_lbl.setMinimumWidth(80)
        row_prev_layout.addWidget(prev_lbl)
        row_prev_layout.addWidget(self.le_prev_pid)
        pid_layout.addLayout(row_prev_layout)

        pid_layout.addSpacing(20) # PID 状态之间的间距

        # 当前 PID (Curr PID)
        self.le_curr_pid = QLineEdit(f"Kp: --- | Ki: --- | Kd: ---")
        self.le_curr_pid.setReadOnly(True)
        self.le_curr_pid.setAlignment(Qt.AlignCenter)
        self.le_curr_pid.setStyleSheet("""
            QLineEdit {
                background-color: #05080f; 
                color: #00ffcc; 
                font-weight: bold; 
                border: 1px solid #00ffcc;
            }
        """)
        row_curr_layout = QHBoxLayout()
        curr_lbl = QLabel("Curr PID"); curr_lbl.setMinimumWidth(80)
        row_curr_layout.addWidget(curr_lbl)
        row_curr_layout.addWidget(self.le_curr_pid)
        pid_layout.addLayout(row_curr_layout)
        ai_analysis_layout.addLayout(pid_layout)

        group_ai_analysis.setLayout(ai_analysis_layout)
        tuning_layout.addWidget(group_ai_analysis)

        # 底部按钮
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self.start_tuning)
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.clicked.connect(self.reject)
        self.btn_pause = QPushButton("LLM API TEST")
        self.btn_pause.setObjectName("btn_api_test")
        self.btn_pause.clicked.connect(self.test_llm_api)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_pause)
        tuning_layout.addLayout(btn_layout)
       

    def start_tuning(self):
        self.btn_start.setEnabled(False)

        if self.tuning_thread is None or not self.tuning_thread.isRunning():
            self.tuning_thread = AITuningThread(self.parent_app, self)
            self.tuning_thread.tuning_log_signal.connect(self.txt_ai_console.append)
            self.tuning_thread.command_signal.connect(self.parent_app.send_command)
            self.tuning_thread.pid_update_signal.connect(self.update_pid_display)
            self.tuning_thread.finished_signal.connect(self.on_tuning_finished)
            self.tuning_thread.start_record_signal.connect(self.parent_app.on_start_episode)
            self.tuning_thread.stop_record_signal.connect(self.parent_app.on_stop_episode)
            
            self.tuning_thread.start()

    def update_pid_display(self, pid_dict):
        p = pid_dict.get('kp', 0.0)
        i = pid_dict.get('ki', 0.0)
        d = pid_dict.get('kd', 0.0)
        current_text = self.le_curr_pid.text()
        if "---" not in current_text: # 如果不是初始状态
            self.le_prev_pid.setText(current_text)
            
        # 刷新当前的 PID
        self.le_curr_pid.setText(f"Kp: {p:.2f} | Ki: {i:.2f} | Kd: {d:.2f}")

    def test_llm_api(self):
        """触发 API 测试"""
        self.txt_ai_console.append("\n[API Test] 正在测试大模型 API 连通性，请稍候...")
        self.btn_pause.setEnabled(False) # 测试期间禁用按钮防连点
        self.btn_start.setEnabled(False) # 连通性测试期间也不允许开始调参
        
        # 启动后台测试线程
        self.api_test_thread = APITestThread(self.tuner)
        self.api_test_thread.result_signal.connect(self.on_api_test_result)
        self.api_test_thread.start()

    def on_api_test_result(self, success, msg):
        """接收 API 测试结果的回调函数"""
        self.btn_pause.setEnabled(True)
        self.btn_start.setEnabled(True)
        
        if success:
            self.txt_ai_console.setTextColor(QColor("#00ff00"))
            self.txt_ai_console.append(f"[API Test OK] {msg}")
        else:
            self.txt_ai_console.setTextColor(QColor("#ff4444"))
            self.txt_ai_console.append(f"[API Test Failed] {msg}")
            
        self.txt_ai_console.setTextColor(QColor("#00e5ff")) # 恢复默认色
        self.txt_ai_console.verticalScrollBar().setValue(self.txt_ai_console.verticalScrollBar().maximum())

    def reject(self):
        if self.tuning_thread and self.tuning_thread.isRunning():
            self.tuning_thread.stop()
            self.btn_start.setEnabled(True)
        super().reject()

    def on_tuning_finished(self):
        self.txt_ai_console.append("\n[AI Tuning] Process has finished.")
        self.btn_start.setEnabled(True)