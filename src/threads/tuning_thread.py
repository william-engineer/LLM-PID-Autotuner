import time
import re
import random
import logging
from PyQt5.QtCore import QThread, pyqtSignal
import debugpy

from core.metrics import calculate_episode_metrics
from core.data_logger import DataLogger

class AITuningThread(QThread):  
    tuning_log_signal = pyqtSignal(str) # 参数: 日志字符串
    command_signal = pyqtSignal(str) # 参数: 串口命令字符串
    pid_update_signal = pyqtSignal(dict) # 参数: 新 PID 参数字典
    finished_signal = pyqtSignal()
    start_record_signal = pyqtSignal(int, float, float, float) # round_num, p, i, d
    stop_record_signal = pyqtSignal()

    def __init__(self, parent_app, dialog):
        super().__init__()
        self.parent_app = parent_app
        self.dialog = dialog
        self.is_running = True
        self.round_num = 0

    def run(self):
        max_rounds = self.parent_app.sp_maxrounds.value()
        cooldown_temp = self.parent_app.sp_cooldown.value()
        setpoint = self.parent_app.sp_target.value()
        stable_dur = self.parent_app.sp_stable_dur.value()
        timeout = self.parent_app.sp_timeout.value()
        stable_band = self.parent_app.sp_stable_band.value()
        overshoot_thresh = self.parent_app.sp_overshoot.value()        

        if "---" in self.dialog.le_curr_pid.text(): 
            self.tuning_log_signal.emit("\nPlease send get-pid command before starting AI tuning.")
            self.finished_signal.emit()
            return

        m = re.search(r'Kp:\s*([+-]?\d*\.?\d+)\s*\|\s*Ki:\s*([+-]?\d*\.?\d+)\s*\|\s*Kd:\s*([+-]?\d*\.?\d+)', self.dialog.le_curr_pid.text())
        current_p, current_i, current_d = (float(x) for x in m.groups()) if m else (None, None, None)

        self.tuning_log_signal.emit("Starting AI tuning process...")
        while self.is_running and self.round_num < max_rounds:
            self.round_num += 1
            self.tuning_log_signal.emit(f"\n=== Round {self.round_num} 准备测试 ===")

            # 降温等待阶段
            self.tuning_log_signal.emit(f"[系统降温] 发送 STOP 指令，等待温度降至 {cooldown_temp}°C 以下...")
            self.command_signal.emit("stop") # 发送停止/冷却指令
            self.command_signal.emit("forced-cooling on")
            while self.is_running:
                current_t = self.parent_app.latest_temp
                if current_t <= cooldown_temp:
                    self.tuning_log_signal.emit(f"[降温完成] 当前温度: {current_t:.1f}°C，系统已冷却。")
                    self.command_signal.emit("forced-cooling off")
                    break
                self.msleep(100)

            if not self.is_running:
                break # 如果在此期间用户点击了 STOP，退出流程

            #AI 调参
            # 1. 发送set-pid 指令，开始新一轮测试
            # 2. 发送start指令启动设备
            # 3. 解析Data Console数据，每收集 20 个数据点，进行一次动态评估calculate_episode_metrics
            # 4. 如果超时都没满足要求，超时结束本轮测试
            # 5. 分析曲线数据calculate_episode_metrics，得出本轮测试的性能指标（如超调量、稳态误差、响应时间等）
            # 6. 判定是否达到预设的性能目标，如果达到则提前结束调参流程；如果未达到，调用 LLM 分析本轮测试结果并给出下一轮 PID 参数建议
            self.pid_update_signal.emit({'kp': current_p, 'ki': current_i, 'kd': current_d})
            self.command_signal.emit(f"set-pid kp {current_p:.2f} ki {current_i:.2f} kd {current_d:.2f}")
            self.msleep(1000)

            start_temp = self.parent_app.latest_temp
            self.start_record_signal.emit(self.round_num, current_p, current_i, current_d)
            self.command_signal.emit("start")

            episode_start = time.time()
            metrics = None

            self.tuning_log_signal.emit(f"[测试中] 目标温度: {setpoint}°C，正在收集阶跃响应数据...")
            stop_condition = 'UNKNOWN'
            while self.is_running:
                self.msleep(2000) # 每 2 秒评估一次当前曲线
                duration = time.time() - episode_start

                # 获取本轮正在录制的数据进行分析
                times, temps = self.parent_app.get_current_episode_data()
                if not times or len(times) < 5:
                    continue

                metrics = calculate_episode_metrics(times, temps, setpoint, start_temp, stable_band, stable_dur)

                logging.debug(f"Debug: Round {self.round_num} - Duration: {duration:.1f}s, Metrics: {metrics}")
                print(f"Debug: Round {self.round_num} - Duration: {duration:.1f}s, Metrics: {metrics}")
                if metrics:
                    # 提前终止条件 1：系统完美稳定了指定的时间
                    if metrics['stable_duration'] >= stable_dur:
                        self.tuning_log_signal.emit(f"[触发终止] 系统完美稳定了 {stable_dur} 秒。")
                        stop_condition = 'STABLE'
                        break
                    # 【提前终止 2】：识别趴平卡死
                    if metrics.get('is_stuck', False):
                        stop_condition = metrics['status']
                        self.tuning_log_signal.emit(f"[触发终止] 诊断: {metrics['overall_status']}。")
                        break
                    # 【提前终止 3】：识别等幅震荡 (曲线4)
                    if metrics['status'] == 'LIMIT_CYCLE_OSCILLATION':
                         self.tuning_log_signal.emit(f"[触发终止] 诊断: 曲线持续等幅震荡，无需干等超时。")
                         stop_condition = 'LIMIT_CYCLE_OSCILLATION'
                         break
                    if metrics['status'] == 'CONVERGING_OSCILLATION':
                         if random.random() < 0.1: # 节流打印，避免刷屏
                             self.tuning_log_signal.emit(f"[监控中] 诊断: 曲线震荡收敛中，等待其最终稳定...")

                if duration > timeout:
                    self.tuning_log_signal.emit(f"[触发终止] 达到最大测试超时时间 ({timeout}s)。")
                    stop_condition = 'TIMEOUT'
                    break

            # 停止记录本轮曲线
            self.stop_record_signal.emit()
            self.command_signal.emit("stop")

            # 保存本轮 AI 调参过程的完整数据为 CSV
            times, temps = self.parent_app.get_current_episode_data()
            if times and temps:
                DataLogger.save_ai_episode(times, setpoint, temps, self.round_num, current_p, current_i, current_d)
                if not self.is_running: break

            self.tuning_log_signal.emit("\n[分析阶段] 正在分析本轮曲线数据...")

            if not metrics:
                self.tuning_log_signal.emit("[错误] 本轮数据不足以计算指标，跳过本轮。")
                continue


            is_sluggish = False
            sluggish_reason = ""
            
            # 这两种情况属于 P 严重不足，自己解决
            if stop_condition == 'FATAL_HEATING_STUCK':
                is_sluggish = True
                sluggish_reason = "加热严重不足，在低温处停滞趴平"
            elif stop_condition == 'OUT_BAND_SSE_STUCK':
                is_sluggish = False
                sluggish_reason = "从未进入过目标带，存在静态误差"
            elif stop_condition == 'TIMEOUT' and not metrics.get('has_entered_band', False):
                is_sluggish = True
                sluggish_reason = "曲线上升极其缓慢 (超时未达标)"

            if is_sluggish:
                self.tuning_log_signal.emit(f"[规则干预] 诊断: {sluggish_reason}。跳过 LLM 分析。")
                temp_kp = current_p
                
                # 尝试自动增大 P。
                current_p = current_p + current_p / 2.0
                self.tuning_log_signal.emit(f"  [执行动作] 自动大幅增大比例项 P: {temp_kp:.4f} -> {current_p:.4f}")
                continue # 直接进入下一轮测试!

            rise_str = f"{metrics['rise_time']:.2f}" if metrics['rise_time'] is not None else "N/A"
            settling_str = f"{metrics['settling_time']:.2f}" if metrics['settling_time'] is not None else "N/A"
            self.tuning_log_signal.emit(f"  测试结果: 状态={metrics['status']}")
            self.tuning_log_signal.emit(f"  指标: 超调={metrics['overshoot']:.1f}°C ({metrics['overshoot_percent']:.1f}%), "
                  f"稳态误差={metrics['steady_state_error']:.2f}°C, "
                  f"上升时间={rise_str}s, "
                  f"调节时间={settling_str}s")
            
            if metrics['status'] == "STABLE" and stop_condition == 'STABLE' and metrics['steady_state_error'] < 1 and metrics['overshoot'] < overshoot_thresh:
                self.tuning_log_signal.emit("\n[SUCCESS] 调参成功！系统响应已达到完美状态。")
                self.tuning_log_signal.emit("\n[整定PID参数] " + f"P={current_p:.2f}, I={current_i:.2f}, D={current_d:.2f}")
                break
           
            history_text = self.dialog.history.to_prompt_text()
            overall_status = {
                "FATAL_INSUFFICIENT_HEATING": "加热严重不足，系统无法到达目标区域",
                  "CRITICAL_OVERSHOOT": "超调严重，可能导致系统震荡", 
                  "HIGH_OVERSHOOT": "超调较大，系统表现得过于活跃", 
                  "MILD_OVERSHOOT": "轻微超调，属于可接受范围，但非最优", 
                  "LARGE_STEADY_ERROR": "存在明显的稳态误差，无法精准对齐目标", 
                  "MINOR_STEADY_ERROR": "稳态误差仍有提升空间", 
                  "STABLE": "系统表现完美，稳定运行"
            }.get(metrics['status'], "未知状态")
            prompt_data = {
                "current_pid": {"p": current_p, "i": current_i, "d": current_d},
                "setpoint": setpoint,
                "episode_performance": {
                    "overshoot": round(metrics['overshoot'], 2),
                    "overshoot_percentage": round(metrics['overshoot_percent'], 2),
                    "rise_time_seconds": round(metrics['rise_time'], 2) if metrics['rise_time'] is not None else None,
                    "settling_time_seconds": round(metrics['settling_time'], 2) if metrics['settling_time'] is not None else None,
                    "steady_state_error_celsius": round(metrics['steady_state_error'], 2),
                    "stable_duration_seconds": round(metrics['stable_duration'], 2),
                    "overall_status": overall_status
                }
            }
            
            self.tuning_log_signal.emit("-> 正在请求 LLM 分析并给出下一轮 PID 建议...")
            prompt = self.parent_app.current_prompt + "\n" + self.parent_app.prompt_format
            result = self.dialog.tuner.analyze(prompt_data, history_text, prompt)
            if result:
                thought = result.get('thought_process', '无分析')
                summary = result.get('analysis_summary', '无思考')
                action = result.get('tuning_action', 'UNKNOWN')

                self.tuning_log_signal.emit(f"\n[LLM 思考过程]:\n{thought}")
                self.tuning_log_signal.emit(f"[LLM 诊断总结]: {summary}")

                # 提取 LLM 给出的下一轮 PID 参数
                try:
                    old_p, old_i, old_d = current_p, current_i, current_d
                    current_p = float(result.get('next_p', current_p))
                    current_i = float(result.get('next_i', current_i))
                    current_d = float(result.get('next_d', current_d))
                    self.tuning_log_signal.emit(f"  [动作] {action}: KP {old_p:.2f}->{current_p:.2f}, KI {old_i:.4f}->{current_i:.2f}, KD {old_d:.2f}->{current_d:.2f}")
                    self.dialog.history.add_record(self.round_num, {'p': current_p, 'i': current_i, 'd': current_d}, metrics, overall_status,summary)
            
                except (ValueError, TypeError):
                    self.tuning_log_signal.emit("[错误] LLM 返回的参数格式不正确，保持当前参数。")

            else:
                self.tuning_log_signal.emit("[错误] LLM 请求失败...")

        self.tuning_log_signal.emit("\nAI tuning process ended or stopped.")
        self.finished_signal.emit()

    def stop(self):
        self.is_running = False
        self.wait()