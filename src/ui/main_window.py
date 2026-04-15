import time
import random
from datetime import datetime
import logging
import serial.tools.list_ports
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QGroupBox, QLabel, QComboBox, QPushButton, 
                             QLineEdit, QSpinBox, QDoubleSpinBox, QLCDNumber, 
                             QTextEdit, QListView, QSizePolicy)
from PyQt5.QtCore import Qt, QTime
from PyQt5.QtGui import QFont, QColor, QPalette
import pyqtgraph as pg

# 引入子模块
from config.settings import SYSTEM_DEFAULT_PROMPT, PROMPT_FORMAT
from hardware.serial_port import SerialPort
from threads.serial_thread import SerialThread
from ui.widgets.custom_groupbox import DoubleClickTitleGroupBox
from ui.dialogs.parse_format import ParseFormatDialog
from ui.dialogs.chart_config import ChartConfigDialog
from ui.dialogs.prompt_config import PromptConfigDialog
from ui.dialogs.ai_tuning import AITuningDialog
from core.data_logger import ManualRecorder

class LLMTurningApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLM PID Auto Tuning Expert System v1.1")
        self.resize(1200, 800)
        
        # 初始化数据结构：默认5条曲线的配置和历史数据
        self.time_data = []
        self.next_curve_id = 5
        self.curves = [
            {'id': 0, 'name': 'Target Temp', 'color': "#ff0000", 'visible': True, 'type': 'target', 'abs_time': [], 'x_data': [], 'y_data': []},
            {'id': 1, 'name': 'Current Temp','color': '#00ffcc', 'visible': True, 'type': 'normal', 'abs_time': [], 'x_data': [], 'y_data': []},
            {'id': 2, 'name': 'P Term',      'color': '#ff00ff', 'visible': False, 'type': 'normal', 'abs_time': [], 'x_data': [], 'y_data': []},
            {'id': 3, 'name': 'I Term',      'color': '#ffff00', 'visible': False, 'type': 'normal', 'abs_time': [], 'x_data': [], 'y_data': []},
            {'id': 4, 'name': 'D Term',      'color': '#00ffff', 'visible': False, 'type': 'normal', 'abs_time': [], 'x_data': [], 'y_data': []}
        ]
        self.curve_items = {}
        self.serial_thread = None
        self.latest_temp = 0.0
        self.normal_start_time = 0.0
        self.open_turning = False
        self.ai_tuning_dialog = None
        self.is_recording_episode = False     # 是否正在录制回合数据
        self.episode_start_time = 0.0         # 本回合的绝对起始时间
        self.current_tuning_curve_id = None   # 当前回合对应的曲线 ID
        self.manual_recorder = ManualRecorder()

        self.system_default_prompt = SYSTEM_DEFAULT_PROMPT
        self.current_prompt = self.system_default_prompt
        self.prompt_format = PROMPT_FORMAT
        self.init_ui()

    def init_ui(self):
        # --- 全局样式表 ---
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0b0f19; color: #00ffcc; font-family: 'Consolas', monospace; }
            QGroupBox { border: 1px solid #1a2a3a; border-radius: 5px; margin-top: 2ex; font-weight: bold; color: #88aaff; }
            QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }
            QPushButton { background-color: #111827; border: 1px solid #00ffcc; border-radius: 4px; color: #00ffcc; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: rgba(0, 255, 204, 0.2); }
            QPushButton:pressed { background-color: #00ffcc; color: #0b0f19; }
            QLineEdit, QSpinBox, QDoubleSpinBox { background-color: #05080f; border: 1px solid #334455; color: #ffffff; padding: 4px; border-radius: 3px; }
            QComboBox { 
                background-color: #05080f; 
                border: 1px solid #334455; 
                color: #ffffff; 
                padding: 4px 10px; /* 增加左右内边距，防止文字太靠边 */
                border-radius: 3px; 
                min-width: 80px; /* 保证最小宽度 */
            }
            QComboBox:focus { border: 1px solid #00ffcc; }
            /* QComboBox 下拉菜单列表样式 */
            QComboBox QAbstractItemView {
                background-color: #0b0f19; /* 下拉框背景色 */
                color: #00ffcc;            /* 荧光青文字 */
                border: 1px solid #00ffcc; /* 发光边框 */
                selection-background-color: rgba(0, 255, 204, 0.3); /* 选中项的半透明背景 */
                selection-color: #ffffff;  /* 选中项的文字变白 */
                outline: 0px;              /* 去除默认虚线框 */
            }               
            QTextEdit { background-color: #000000; border: 1px solid #1a2a3a; color: #00ff00; }
            QLabel { color: #ffffff; }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # ================= 左侧：控制与配置区域 =================
        left_panel = QVBoxLayout()
        left_panel.setSpacing(15)

        # 1. 串口设置
        group_serial = QGroupBox("Serial Setup")
        layout_serial = QVBoxLayout()
        

        row1_serial = QHBoxLayout()
        row1_serial.addWidget(QLabel("Port:"))
        self.cb_port = QComboBox(); 
        self.refresh_serial_ports()
        list_view = QListView()
        self.cb_port.setView(list_view)
        self.cb_port.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        list_view.setMinimumWidth(280)
        row1_serial.addWidget(self.cb_port)

        row1_serial.addWidget(QLabel("Baud:"))
        self.cb_baud = QComboBox(); 
        self.cb_baud.addItems(["2400", "4800", "9600", "19200", "38400", "56000", "115200", "921600"]); 
        self.cb_baud.setCurrentText("115200")
        self.cb_baud.setView(QListView())
        row1_serial.addWidget(self.cb_baud)
        layout_serial.addLayout(row1_serial)

        layout_serial_btn = QHBoxLayout()
        self.btn_connect = QPushButton("CONNECT")
        self.btn_refresh = QPushButton("REFRESH")
        self.btn_refresh.clicked.connect(self.refresh_serial_ports)
        self.btn_connect.clicked.connect(self.toggle_serial_connection)
        layout_serial_btn.addWidget(self.btn_refresh,1)
        layout_serial_btn.addWidget(self.btn_connect,2)
        layout_serial.addLayout(layout_serial_btn)
        group_serial.setLayout(layout_serial)
        left_panel.addWidget(group_serial)

        # 2. 系统配置 - API 设置
        group_api = QGroupBox("LLM API Setup")
        layout_api = QVBoxLayout()
        def add_form_row(layout, label_text, label_width, widget):
            row = QHBoxLayout()
            lbl = QLabel(label_text); lbl.setMinimumWidth(label_width)
            row.addWidget(lbl)
            row.addWidget(widget)
            layout.addLayout(row)

        self.le_base_url = QLineEdit("https://api.deepseek.com")
        self.le_api_key = QLineEdit("*****************"); self.le_api_key.setEchoMode(QLineEdit.PasswordEchoOnEdit)

        self.cb_model = QComboBox(); 
        self.cb_model.addItems(["deepseek-chat", "deepseek-reasoner"])
        self.cb_model.setView(QListView())
        self.cb_model.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self.le_provider = QLineEdit("openai")
        add_form_row(layout_api, "Base URL", 80, self.le_base_url)
        add_form_row(layout_api, "API Key", 80, self.le_api_key)
        add_form_row(layout_api, "Model", 80, self.cb_model)
        add_form_row(layout_api, "Provider", 80, self.le_provider)
        api_btn_layout = QHBoxLayout()
        btn_prompt = QPushButton("PROMPT")
        btn_ai_tuning = QPushButton("AI TUNING")
        btn_prompt.clicked.connect(self.open_prompt_config)
        btn_ai_tuning.clicked.connect(self.open_ai_tuning_dialog)
        api_btn_layout.addWidget(btn_prompt, 1) 
        api_btn_layout.addWidget(btn_ai_tuning, 2) 
        layout_api.addLayout(api_btn_layout)
        group_api.setLayout(layout_api)
        left_panel.addWidget(group_api)

        # 3. 阈值设置
        group_tune = QGroupBox("Tuning Thresholds")
        layout_tune = QVBoxLayout()
        self.sp_maxrounds = QSpinBox(); self.sp_maxrounds.setValue(10)
        self.sp_target = QDoubleSpinBox(); self.sp_target.setRange(0,1000); self.sp_target.setValue(60.0)
        self.sp_cooldown = QDoubleSpinBox(); self.sp_cooldown.setRange(0,1000); self.sp_cooldown.setValue(30.0)
        self.sp_timeout = QSpinBox(); self.sp_timeout.setRange(0, 3600); self.sp_timeout.setValue(600)
        self.sp_stable_dur = QDoubleSpinBox(); self.sp_stable_dur.setRange(0,3600); self.sp_stable_dur.setValue(60.0)
        self.sp_overshoot = QDoubleSpinBox(); self.sp_overshoot.setValue(2.0)
        self.sp_stable_band = QDoubleSpinBox(); self.sp_stable_band.setValue(1.0)

        add_form_row(layout_tune, "Max Rounds", 100, self.sp_maxrounds)
        add_form_row(layout_tune, "Target (°C)", 100, self.sp_target)
        add_form_row(layout_tune, "Cool Down (°C)", 100, self.sp_cooldown)
        add_form_row(layout_tune, "Timeout (s)", 100, self.sp_timeout)
        add_form_row(layout_tune, "Stable Dur(s)", 100, self.sp_stable_dur)
        add_form_row(layout_tune, "Overshoot(°C)", 100, self.sp_overshoot)
        add_form_row(layout_tune, "Stable Band(°C)", 100, self.sp_stable_band)
       
        group_tune.setLayout(layout_tune)
        left_panel.addWidget(group_tune)
        left_panel.addStretch()

        # ================= 右侧：可视化与终端区域 =================
        right_panel = QVBoxLayout()
        top_header_layout = QHBoxLayout()
        
        # LCD 温度显示
        lcd_layout = QHBoxLayout()
        self.lcd = QLCDNumber()
        self.lcd.setDigitCount(5)
        self.lcd.setMinimumSize(150, 60)
        self.lcd.setSegmentStyle(QLCDNumber.Flat)
        lcd_palette = self.lcd.palette()
        lcd_palette.setColor(QPalette.WindowText, QColor(0, 255, 0))
        lcd_palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.lcd.setPalette(lcd_palette)
        self.lcd.setAutoFillBackground(True)
        self.lcd.display("0.0")
        lcd_layout.addWidget(self.lcd)
        
        lbl_unit = QLabel("°C")
        lbl_unit.setFont(QFont("Consolas", 20, QFont.Bold))
        lbl_unit.setStyleSheet("color: #00ff00;")
        lcd_layout.addWidget(lbl_unit)
        top_header_layout.addLayout(lcd_layout, stretch=1)
        
        # 软件名称和作者
        title_layout = QVBoxLayout()
        title_label = QLabel("LLM PID Auto Tuning Expert System")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #00ffcc; font-size: 24px; font-weight: bold;")
        
        author_label = QLabel("Copyright © 2026 William Chen")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("color: #88aaff; font-size: 14px;")


        title_layout.addWidget(title_label)
        title_layout.addWidget(author_label)
        top_header_layout.addLayout(title_layout, stretch=3)
        
        # 图表配置按钮
        config_layout = QVBoxLayout()
        config_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        btn_chart_config = QPushButton("Chart Settings")
        btn_chart_config.setMinimumSize(120, 40)
        btn_chart_config.setStyleSheet("border: 1px solid #00aaff; color: #00aaff;")
        btn_chart_config.clicked.connect(self.open_chart_config)
        config_layout.addWidget(btn_chart_config)
        top_header_layout.addLayout(config_layout, stretch=1)

        right_panel.addLayout(top_header_layout)

        # pyqtgraph 温度波形图
        pg.setConfigOption('background', '#000000')
        pg.setConfigOption('foreground', '#ffffff')
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Value')
        self.plot_widget.setLabel('bottom', 'Time', units='s')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setYRange(0, 80)
        
        # 初始绘制曲线和图例
        self.rebuild_plot()
        right_panel.addWidget(self.plot_widget, stretch=5)

        # 终端与命令中心
        bottom_layout = QHBoxLayout()
        
        # 左侧日志终端
        group_console = DoubleClickTitleGroupBox("DATA CONSOLE")
        group_console.setToolTip("Double-click the title to view parsing format.")
        group_console.titleDoubleClicked.connect(self.open_parse_format_dialog)
        console_layout = QVBoxLayout()
        console_layout.setSpacing(0)
        self.txt_data_console = QTextEdit()
        self.txt_data_console.setReadOnly(True)
        self.txt_data_console.setStyleSheet("""
            QTextEdit {
                background-color: #000000; 
                border: 1px solid #1a2a3a; 
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
                color: #00ff00;
            }
        """)
        console_layout.addWidget(self.txt_data_console)

        self.btn_record = QPushButton("⏺ START RECORDING")
        self.btn_record.setCheckable(True) # 设为 Checkable，利用 CSS 伪类控制状态
        self.btn_record.setFixedHeight(24)
        self.btn_record.setStyleSheet("""
            QPushButton { 
                background-color: #0b0f19;
                border: 1px solid #1a2a3a; 
                border-top: 1px dashed #334455;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
                color: #556677; 
                font-size: 11pt;
            }
            QPushButton:hover { 
                color: #00ffcc; 
                background-color: #111827; 
            }
            QPushButton:checked { 
                background-color: #330000; 
                color: #ff4444; 
                border: 1px solid #ff4444; 
                border-top: 1px solid #ff4444;
            }
        """)
        self.btn_record.clicked.connect(self.toggle_manual_recording)
        console_layout.addWidget(self.btn_record)
     
        group_console.setLayout(console_layout)
        bottom_layout.addWidget(group_console, stretch=6)

        # 右侧快捷指令中心
        group_cmd = QGroupBox("COMMAND CENTER")
        cmd_layout = QVBoxLayout()
        
        self.txt_command_center = QTextEdit()
        self.txt_command_center.setReadOnly(True)
        self.txt_command_center.setPlaceholderText("Wait for command response...")
        self.txt_command_center.setStyleSheet("color: #00e5ff;") 
        cmd_layout.addWidget(self.txt_command_center, stretch=7)
        input_layout = QHBoxLayout()
        self.le_cmd = QLineEdit(); self.le_cmd.setPlaceholderText("ENTER help to see commands list...")
        self.btn_send = QPushButton("SEND")
        input_layout.addWidget(self.le_cmd)
        input_layout.addWidget(self.btn_send)
        self.btn_send.clicked.connect(self.send_command_from_input)
        cmd_layout.addLayout(input_layout)

        quick_btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("START")
        self.btn_stop = QPushButton("STOP")
        self.btn_cool = QPushButton("COOL")
        self.btn_get_pid = QPushButton("GET PID")
        for btn in [self.btn_start, self.btn_stop, self.btn_cool, self.btn_get_pid]:
            btn.setFixedHeight(30)
            quick_btn_layout.addWidget(btn)
            btn.clicked.connect(lambda checked, b=btn: self.send_command_from_quick_btn(b.text()))

        cmd_layout.addLayout(quick_btn_layout)
        group_cmd.setLayout(cmd_layout)
        bottom_layout.addWidget(group_cmd, stretch=5)
        right_panel.addLayout(bottom_layout, stretch=2)
        
        main_layout.addLayout(left_panel, stretch=2)
        main_layout.addLayout(right_panel, stretch=8)

    def restart_normal_curves(self):
        """清空普通曲线数据，时间轴归零，重新开始绘制"""
        self.normal_start_time = time.time()
        
        for cfg in self.curves:
            if cfg.get('type') in ['normal', 'target']:
                cfg['x_data'].clear()
                cfg['y_data'].clear()
                if 'abs_time' in cfg:
                    cfg['abs_time'].clear()
                # 确保进入普通模式时，Current 和 Target 默认可见
                if cfg['id'] in [0, 1]: 
                    cfg['visible'] = True
                    
        self.rebuild_plot()
        self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis)
        self.plot_widget.getViewBox().setLimits(xMin=0)

    # 刷新串口
    def refresh_serial_ports(self):
        """刷新系统可用串口列表"""
        self.cb_port.clear()
        ports = serial.tools.list_ports.comports()
        if not ports:
            self.cb_port.addItem("No ports found")
            self.txt_command_center.setTextColor(Qt.yellow)
            self.txt_command_center.append("[WARN] No serial ports detected!")
            return
        for port in ports:
            # 显示格式: COM5 - USB Serial Port
            port_info = f"{port.device}"
            if port.description:
                port_info += f" - {port.description}"
            self.cb_port.addItem(port_info, port.device)
        self.cb_port.setCurrentIndex(0)    

    # 连接/断开串口
    def toggle_serial_connection(self):
        """连接/断开串口"""
        if self.btn_connect.text() == "CONNECT":
            selected_port = self.cb_port.currentData()
            if not selected_port or selected_port == "No ports found":
                self.txt_command_center.setTextColor(Qt.red)
                self.txt_command_center.append("[ERROR] Please select a valid port!")
                return
            
            baudrate = int(self.cb_baud.currentText())
            try:
                self.serial_controller = SerialPort(selected_port, baudrate)
                if self.serial_controller.connect():
                    self.btn_connect.setText("DISCONNECT")
                    self.btn_connect.setStyleSheet("background-color: #116611; border: 1px solid #00ff00;")
                    self.serial_thread = SerialThread(self.serial_controller.serial)
                    self.serial_thread.data_received_signal.connect(self.handle_serial_data)
                    self.serial_thread.command_received_signal.connect(self.handle_serial_command)
                    self.start_time = None

                    self.restart_normal_curves()
                    self.serial_thread.start()
                else:
                    self.txt_command_center.setTextColor(Qt.red)
                    self.txt_command_center.append(f"[ERROR] Failed to connect to {selected_port}")
            except Exception as e:
                self.txt_command_center.setTextColor(Qt.red)
                self.txt_command_center.append(f"[EXCEPTION] {str(e)}")
        else:
            if self.serial_thread and self.serial_thread.isRunning():
                self.serial_thread.stop()

            if hasattr(self, 'serial_controller'):
                self.serial_controller.disconnect()
            self.btn_connect.setText("CONNECT")
            self.btn_connect.setStyleSheet("background-color: #111827; border: 1px solid #00ffcc;")
            
    
    def handle_serial_data(self, data_list, raw_str):
        """处理从串口接收到的数据"""
        current_time = time.time()

        if getattr(self, 'start_time', None) is None:
            self.start_time = current_time

        val = float(data_list[1]) if 1 < len(data_list) else 0.0  # 当前温度
        self.latest_temp = val
        self.lcd.display(f"{val:.1f}")
        target_val = self.sp_target.value()

        # 手动数据记录功能：如果已开启记录，把当前数据行写入CSV
        if self.manual_recorder.is_recording:
            self.manual_recorder.write_row(current_time, data_list)

        if not self.open_turning:
            # 串口数据示波器模式
            t = current_time - self.normal_start_time

            # 拉长目标温度线
            self.curves[0]['x_data'] = [0, max(t, self.curves[0]['x_data'][-1] if self.curves[0]['x_data'] else 0)]
            self.curves[0]['y_data'] = [target_val, target_val]
            if 0 in self.curve_items:
                self.curve_items[0].setData(self.curves[0]['x_data'], self.curves[0]['y_data'])
            
            # 更新所有可见的 normal 曲线 (主要是 Current Temp)
            for i, cfg in enumerate(self.curves):
                if cfg.get('type') == 'normal':
                    v = float(data_list[i]) if i < len(data_list) else 0.0 
                    cfg['abs_time'].append(current_time)
                    cfg['x_data'].append(t)
                    cfg['y_data'].append(v)
                    if cfg['id'] in self.curve_items:
                        self.curve_items[cfg['id']].setData(cfg['x_data'], cfg['y_data'])
        else:
            # AI 调参模式
            if self.is_recording_episode and self.current_tuning_curve_id is not None:
                t = current_time - self.episode_start_time # 本回合的相对时间 (必定从 0 开始)

                # 拉长目标温度线
                self.curves[0]['x_data'] = [0, max(t, self.curves[0]['x_data'][-1] if self.curves[0]['x_data'] else 0)]
                self.curves[0]['y_data'] = [target_val, target_val]
                if 0 in self.curve_items:
                    self.curve_items[0].setData(self.curves[0]['x_data'], self.curves[0]['y_data'])

                # 更新当前这一轮测试新增的那根曲线
                for cfg in self.curves:
                    if cfg['id'] == self.current_tuning_curve_id:
                        cfg['abs_time'].append(current_time)
                        cfg['x_data'].append(t)
                        cfg['y_data'].append(val)
                        if cfg['id'] in self.curve_items:
                            self.curve_items[cfg['id']].setData(cfg['x_data'], cfg['y_data'])
                        break
        # 日志终端显示原始数据
        time_str = datetime.now().strftime("%H:%M:%S.%f")[:-3] 
        self.txt_data_console.append(f"[{time_str}] RX: {raw_str}")
        self.txt_data_console.verticalScrollBar().setValue(self.txt_data_console.verticalScrollBar().maximum())        

    def handle_serial_command(self, raw_str):
        """处理从串口接收到的命令"""
        time_str = QTime.currentTime().toString("hh:mm:ss")
        self.txt_command_center.append(f"[{time_str}] : {raw_str}")
        # 解析PID命令示例: "kp=1.2 ki=0.5 kd=0.1"
        if raw_str.startswith("kp="):
            try:
                parts = raw_str.split()
                kp = float(parts[0].split('=')[1])
                ki = float(parts[1].split('=')[1])
                kd = float(parts[2].split('=')[1])
                if self.ai_tuning_dialog:
                    self.ai_tuning_dialog.le_curr_pid.setText(f"Kp: {kp:.2f} | Ki: {ki:.2f} | Kd: {kd:.2f}")
                    self.ai_tuning_dialog.le_prev_pid.setText(f"Kp: {kp:.2f} | Ki: {ki:.2f} | Kd: {kd:.2f}")
            except Exception as e:
                self.txt_command_center.setTextColor(Qt.red)
                self.txt_command_center.append(f"[ERROR] Failed to parse PID command: {str(e)}")
        
        self.txt_command_center.verticalScrollBar().setValue(self.txt_command_center.verticalScrollBar().maximum())

    def send_command(self, cmd_str):
        """发送命令到串口"""
        if hasattr(self, 'serial_controller') and self.serial_controller.serial and self.serial_controller.serial.is_open:
            try:
                self.serial_controller.write_command(cmd_str)
                time_str = QTime.currentTime().toString("hh:mm:ss")
                self.txt_command_center.setTextColor(Qt.cyan)
                self.txt_command_center.append(f"[{time_str}] TX: {cmd_str}")
                self.txt_command_center.verticalScrollBar().setValue(self.txt_command_center.verticalScrollBar().maximum())
            except Exception as e:
                self.txt_command_center.setTextColor(Qt.red)
                self.txt_command_center.append(f"[ERROR] Failed to send command: {str(e)}")
        else:
            self.txt_command_center.setTextColor(Qt.red)
            self.txt_command_center.append("[ERROR] Serial port is not connected!")

    def send_command_from_input(self):
        """从输入框发送命令到串口"""
        cmd = self.le_cmd.text().strip()
        if not cmd:
            return
        self.send_command(cmd)

    def send_command_from_quick_btn(self, btn_text):
        """根据快捷按钮文本发送预设命令"""
        cmd_map = {
            "START": "start",
            "STOP": "stop",
            "COOL": "forced-cooling on",
            "GET PID": "get-pid"
        }
        cmd_str = cmd_map.get(btn_text, "")
        if cmd_str:
            self.send_command(cmd_str)

    def toggle_manual_recording(self):
        """切换手动数据录制状态"""
        if self.btn_record.isChecked():
            if self.manual_recorder.start():
                self.btn_record.setText("🔴 RECORDING IN PROGRESS...")
            else:
                self.btn_record.setChecked(False) # 开启失败时回退按钮状态
        else:
            self.manual_recorder.stop()
            self.btn_record.setText("⏺ START RECORDING")

    def force_stop_manual_recording(self):
        """强制停止手动录制"""
        if self.manual_recorder.is_recording:
            self.manual_recorder.stop()
            self.btn_record.setChecked(False)
            self.btn_record.setText("⏺ START RECORDING")

    def on_start_episode(self, round_num, p, i, d):
        """AI线程发起信号，主程序创建一个新的独立从0开始的曲线"""
        new_id = self.next_curve_id
        self.next_curve_id += 1
        
        # 随机分配一个高亮颜色
        color = f"#{random.randint(50, 255):02x}{random.randint(50, 255):02x}{random.randint(50, 255):02x}"
        
        new_curve = {
            'id': new_id,
            'name': f"R{round_num} (Kp:{p:.2f} Ki:{i:.2f} Kd:{d:.2f})",
            'color': color,
            'visible': True,
            'type': 'ai',
            'abs_time': [],
            'x_data': [],
            'y_data': []
        }
        self.curves.append(new_curve)
        self.rebuild_plot() # 重新生成图例和图形对象
        
        self.current_tuning_curve_id = new_id
        self.episode_start_time = time.time()
        self.is_recording_episode = True
        
        # 每次新回合，把目标曲线的 X 轴也清零，跟着新曲线一起从左画到右
        if 0 < len(self.curves):
            self.curves[0]['abs_time'].clear()
            self.curves[0]['x_data'].clear()
            self.curves[0]['y_data'].clear()

        self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis)
        self.plot_widget.getViewBox().setLimits(xMin=0)

    def on_stop_episode(self):
        """停止录制本轮回合数据"""
        self.is_recording_episode = False

    def get_current_episode_data(self):
        """提供当前正在录制回合的 X/Y 数组"""
        for cfg in self.curves:
            if cfg['id'] == self.current_tuning_curve_id:
                return cfg['x_data'], cfg['y_data']
        return [], []


    def set_api_and_threshold_enabled(self, enabled: bool):
        # API 区
        self.le_base_url.setEnabled(enabled)
        self.le_api_key.setEnabled(enabled)
        self.cb_model.setEnabled(enabled)
        self.le_provider.setEnabled(enabled)

        # 阈值区
        self.sp_maxrounds.setEnabled(enabled)
        self.sp_target.setEnabled(enabled)
        self.sp_cooldown.setEnabled(enabled)
        self.sp_timeout.setEnabled(enabled)
        self.sp_stable_dur.setEnabled(enabled)
        self.sp_overshoot.setEnabled(enabled)
        self.sp_stable_band.setEnabled(enabled)


    #  图表重绘函数
    def rebuild_plot(self):
        """重新构建图表和图例 (用于配置更新后)"""
        self.plot_widget.clear()
    
        if hasattr(self, 'legends'):
            for leg in self.legends:
                if leg.scene() is not None:
                    leg.scene().removeItem(leg)

        self.legends = []
        self.curve_items.clear()
        visible_curves = [cfg for cfg in self.curves if cfg['visible']]
    
        #  画出所有曲线
        for cfg in visible_curves:
            pen = pg.mkPen(color=cfg['color'], width=1.5)
            # 为了叠图好看，在调参模式下关闭区域填充
            if cfg['name'] == 'Current Temp' and not self.open_turning:
                brush = pg.mkBrush(color=QColor(cfg['color']).lighter(100).name() + '33')
                curve = self.plot_widget.plot(pen=pen, fillLevel=0, brush=brush)
            elif 'Target Temp' in cfg['name']:
                boldpen = pg.mkPen(color=cfg['color'], width=3)
                curve = self.plot_widget.plot(pen=boldpen)
            else:
                curve = self.plot_widget.plot(pen=pen)
                
            self.curve_items[cfg['id']] = curve
            
            # 恢复历史数据
            if len(cfg['x_data']) > 0:
                curve.setData(cfg['x_data'], cfg['y_data'])

        # 分列：每 10 个生成一个独立图例，自右向左自动拼接
        group_size = 10
        for i in range(0, len(visible_curves), group_size):
            group_cfg = visible_curves[i:i+group_size]
            
            # 计算这组图例的 X 偏移量 (第1列贴近右边缘，第2列向左移动 160 像素)
            col_idx = i // group_size
            offset_x = -20 - (col_idx * 260)
            
            # 创建独立的图例框，牢牢锚定在右下角
            leg = pg.LegendItem(offset=(offset_x, -20))
            leg.setParentItem(self.plot_widget.getPlotItem().vb)
            
            # 把这组的曲线精确塞进这个独立的图例框中
            for cfg in group_cfg:
                curve = self.curve_items[cfg['id']]
                leg.addItem(curve, cfg['name'])
                
            leg.layout.setVerticalSpacing(2) # 极度紧凑的行间距

            # 遍历并修改刚刚添加进去的字体大小
            for idx, (sample, label) in enumerate(leg.items):
                cfg_name = group_cfg[idx]['name']
                label.setText(cfg_name, size='13pt') 
                
            self.legends.append(leg)

    # 解析格式配置槽函数
    def open_parse_format_dialog(self):
        dialog = ParseFormatDialog(self)
        dialog.exec_()

    #  图表配置槽函数
    def open_chart_config(self):
        dialog = ChartConfigDialog(self)
        dialog.exec_()

    # 提示词修改按钮槽函数
    def open_prompt_config(self):
        dialog = PromptConfigDialog(self)
        dialog.exec_()

    def open_ai_tuning_dialog(self):
        if self.ai_tuning_dialog is not None:
            self.ai_tuning_dialog.activateWindow()
            return
        
        self.force_stop_manual_recording()
        self.set_api_and_threshold_enabled(False)  # 进入页面时锁定
        self.open_turning = True

        for cfg in self.curves:
            if cfg.get('type') == 'normal':
                cfg['visible'] = False
        self.rebuild_plot()

        self.btn_get_pid.click()
        logging.info("Opened AI Tuning Dialog, sent GET PID command to fetch current PID values.")
        self.ai_tuning_dialog = AITuningDialog(self)
        self.ai_tuning_dialog.finished.connect(self.cleanup_after_tuning)     
        self.ai_tuning_dialog.show()   
        
    def cleanup_after_tuning(self):
        """当 AI 调参弹窗关闭时触发的清理逻辑"""
        self.set_api_and_threshold_enabled(True)  # 恢复左侧参数输入框
        self.open_turning = False
        self.ai_tuning_dialog = None
        
        # 退出 AI 模式回到普通模式时，重新从 0 开始绘制 Current Temp 曲线
        self.restart_normal_curves()