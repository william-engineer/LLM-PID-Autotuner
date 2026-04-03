import os
import csv
import time
import logging
from datetime import datetime

class DataLogger:
    @staticmethod
    def save_ai_episode(times, target_val, current_temps, round_num, p, i, d):
        """保存 AI 调参的单回合数据，供后续分析绘图"""
        if not times or not current_temps:
            return

        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        
        dir_path = os.path.join("data", f"AI_{date_str}")
        os.makedirs(dir_path, exist_ok=True)
        
        filename = f"{time_str}_Round{round_num}_Kp{p:.2f}_Ki{i:.2f}_Kd{d:.2f}.csv"
        filepath = os.path.join(dir_path, filename)
        
        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Time(s)", "TargetTemp(C)", "CurrentTemp(C)"])
                for t, curr in zip(times, current_temps):
                    writer.writerow([f"{t:.2f}", f"{target_val:.2f}", f"{curr:.2f}"])
            logging.info(f"AI episode data saved successfully: {filepath}")
        except Exception as e:
            logging.error(f"Failed to save AI episode data: {e}")

class ManualRecorder:
    def __init__(self):
        self.is_recording = False
        self.file_handle = None
        self.writer = None
        self.start_time = 0.0
        self.header_written = False

    def start(self):
        """开始手动记录数据"""
        if self.is_recording:
            return False
        
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        
        dir_path = os.path.join("data", f"DATA_{date_str}")
        os.makedirs(dir_path, exist_ok=True)
        filepath = os.path.join(dir_path, f"{time_str}.csv")
        
        try:
            self.file_handle = open(filepath, 'w', newline='', encoding='utf-8')
            self.writer = csv.writer(self.file_handle)
            self.is_recording = True
            self.header_written = False
            self.start_time = time.time()
            logging.info(f"Started manual recording: {filepath}")
            return True
        except Exception as e:
            logging.error(f"Failed to start manual recording: {e}")
            return False

    def stop(self):
        """停止手动记录数据"""
        if self.is_recording and self.file_handle:
            self.file_handle.close()
            self.file_handle = None
            self.writer = None
            self.is_recording = False
            self.header_written = False
            logging.info("Manual recording stopped.")

    def write_row(self, current_time, data_list):
        """向文件写入一行数据"""
        if self.is_recording and self.writer:
            if not self.header_written:
                headers = ["Time(s)"] + [f"Value_{i+1}" for i in range(len(data_list))]
                self.writer.writerow(headers)
                self.header_written = True

            t = current_time - self.start_time
            row = [f"{t:.2f}"] + [f"{v}" for v in data_list]
            self.writer.writerow(row)
            # 实时刷新磁盘，防止程序意外崩溃时数据丢失
            self.file_handle.flush()