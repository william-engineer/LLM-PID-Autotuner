from PyQt5.QtCore import QThread, pyqtSignal
import logging

class SerialThread(QThread):
    data_received_signal = pyqtSignal(list, str) # 参数: [解析后的浮点数组], 原始字符串
    command_received_signal = pyqtSignal(str) # 参数: 原始字符串

    def __init__(self, serial_instance):
        super().__init__()
        self.serial = serial_instance
        self.is_running = True

    def run(self):
        while self.is_running and self.serial and self.serial.is_open:
            try:
                line = self.serial.readline()
                if line is None:
                    continue
                logging.debug(line)
                raw_str = line.decode('utf-8', errors='ignore').strip()
                if not raw_str:
                    continue

                if raw_str.startswith('$') and raw_str.endswith(';'):
                    data_str = [p for p in raw_str[1:-1].split() if p != '']
                    try:
                        data_list = [float(p) for p in data_str]
                        self.data_received_signal.emit(data_list, raw_str)
                    except Exception:
                        self.command_received_signal.emit(raw_str)
                else:
                    self.command_received_signal.emit(raw_str)      
            except Exception as e:
                logging.error(f"Error reading from serial: {e}")
                continue

    def stop(self):
        self.is_running = False
        self.wait()        