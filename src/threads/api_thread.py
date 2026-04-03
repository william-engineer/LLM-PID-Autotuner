from PyQt5.QtCore import QThread, pyqtSignal

class APITestThread(QThread):
    result_signal = pyqtSignal(bool, str) # 成功标志, 提示信息

    def __init__(self, tuner):
        super().__init__()
        self.tuner = tuner

    def run(self):
        success, msg = self.tuner.test_connection()
        self.result_signal.emit(success, msg)