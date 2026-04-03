# LLM PID Auto Tuning Expert System

## 项目简介 (Introduction)

本项目是一个基于大语言模型 (LLM) 的 PID 参数自整定专家系统。它专门针对具有大惯性、单向加热特性的工业热力系统设计。通过结合 PID 控制理论与人工智能的推理能力，系统能够自动分析温度响应曲线，诊断系统状态，并给出最优的 PID 参数建议。

This project is an LLM-based PID parameter auto-tuning expert system, specifically designed for industrial thermal systems with large inertia and unidirectional heating characteristics. By combining traditional PID control theory with the reasoning capabilities of modern LLMs, the system can automatically analyze temperature response curves, diagnose system states, and provide optimal PID parameter suggestions.

## 软件预览 (Software Preview)

### 主界面 (Main Window)
![Main Window](doc/main%20window.png)

### AI 调参分析 (AI Tuning Analysis)
![AI Analysis](doc/ai%20analysis.png)

## 核心功能 (Key Features)

- **实时可视化 (Real-time Visualization)**: 集成 `pyqtgraph` 实现高频串口数据的实时曲线绘制，支持多条曲线（目标温度、当前温度、P/I/D分量等）对比展示。
- **LLM 智能整定 (LLM Intelligent Tuning)**: 支持 DeepSeek、OpenAI 等大模型接入。利用专家级 Prompt 引导 LLM 对 7 种典型响应曲线（如严重加热不足、持续震荡、超调后稳定等）进行深度诊断。
- **多线程架构 (Multi-threaded Architecture)**: 采用独立的串口读取线程、API 请求线程和调参逻辑线程，确保 UI 界面在高并发数据下依然流畅。
- **专家诊断图谱 (Expert Diagnosis Maps)**: 内置一套成熟的物理指标计算模块 (`metrics.py`)，能够自动计算超调量、上升时间、调节时间、稳态误差及震荡标准差。
- **数据日志记录 (Data Logging)**: 支持将测试过程中的原始串口数据导出为 CSV 格式，方便后续离线分析。
- **灵活配置 (Flexible Configuration)**: 允许用户自定义 LLM 提示词 (Prompt)、调参阈值（最大轮次、目标温度、冷却阈值等）以及图表样式。

## 技术栈 (Tech Stack)

- **Language**: Python 3.x
- **GUI Framework**: PyQt5
- **Visualization**: pyqtgraph, matplotlib
- **Communication**: pyserial
- **AI Integration**: openai SDK (兼容 DeepSeek/OpenAI API)
- **Data Processing**: pandas, numpy

## 项目结构 (Project Structure)

```text
src/
├── main.py                # 程序入口
├── config/
│   └── settings.py        # 全局配置与专家提示词 
├── core/
│   ├── llm_client.py      # LLM API 客户端
│   ├── metrics.py         # 性能指标计算逻辑 
│   ├── data_logger.py     # CSV 数据记录
│   └── tuner_state.py     # 调参状态管理
├── hardware/
│   └── serial_port.py     # 串口底层通信
├── threads/
│   ├── serial_thread.py   # 串口异步处理线程
│   ├── api_thread.py      # LLM 异步请求线程
│   └── tuning_thread.py   # 自动调参逻辑调度线程
└── ui/
    ├── main_window.py     # 主窗体逻辑
    ├── dialogs/           # 各种配置对话框 (Prompt, Chart, AI Tuning etc.)
    └── widgets/           # 自定义 UI 组件
```

## 典型响应曲线诊断 (Curve Diagnosis)

系统将响应结果抽象为以下 7 种模型进行针对性调参：
1. **严重加热不足**: P 项极度缺失。
2. **上升缓慢**: P 项偏小。
3. **理想响应**: 临界阻尼状态，接近最优。
4. **持续震荡**: P 过大或 I 引发相位滞后。
5. **衰减震荡**: 阻尼不足，需微调 D 或 P。
6. **未达标卡死**: 缺少 I 项抹平静差。
7. **达标后稳偏**: 需依靠 I 项精细吃掉残余误差。

## 安装与运行 (Installation & Run)

1. **环境准备**: 确保已安装 Python 3.10+。
2. **安装依赖**:
   ```bash
   pip install -r requirements.txt
   ```
3. **运行程序**:
   ```bash
   python src/main.py
   ```

## 作者 (Author)

**William Chen**  
Copyright © 2026 William Chen. All rights reserved.

## 开源协议 (License)

本项目采用 [GPLv3](LICENSE) 协议开源。

This project is licensed under the terms of the [GPLv3](LICENSE) license.
