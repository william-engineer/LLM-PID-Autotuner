# -*- coding: utf-8 -*-
# LLM PID Auto Tuning Expert System
# Copyright (C) 2026 William Chen
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

from ui.main_window import LLMTurningApp

def main():
    os.makedirs("logs", exist_ok=True)
    
    log_filename = f"logs/app_{datetime.now().strftime('%Y-%m-%d')}.log"

    # 配置全局 logging 设置，使用 handlers 同时输出到文件和控制台
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s - %(module)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'), 
        ]
    )
    # 启用高DPI缩放
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    window = LLMTurningApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()