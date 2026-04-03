import numpy as np

def calculate_episode_metrics(times, inputs, setpoint, start_temp, stable_band, stable_dur):
    """
    =========================================================================================
    工业热力系统 PID 阶跃响应典型曲线特征图谱 (Curve 1 ~ 7)
    =========================================================================================

    【曲线 1】严重加热不足 (低温区趴平卡死)
    - 表现特征：温度在远低于目标值（例如相差 5℃ 以上）的地方彻底平缓，斜率接近 0。
    - 物理意义：比例项(P)极度不足，PID 算出的加热输出完全被环境自然散热抵消，热平衡建立得太早。
    - 应对策略：[启发式旁路] 绝不干等超时，立刻触发熔断。跳过 LLM，直接由代码将 P 翻倍或大幅累加。
    - 对应状态：FATAL_HEATING_STUCK

    【曲线 2】上升极其缓慢 (超时未达标)
    - 表现特征：温度一直在上升（未趴平），但在规定的最大测试时间 (Timeout) 内，连目标温度的边缘都没摸到。
    - 物理意义：比例项(P)偏小，导致加热管功率爬升太慢，系统响应极其迟钝。
    - 应对策略：[启发式旁路] 判定为真缓慢。跳过 LLM，直接由代码自动加大 P，快速逼近目标。
    - 对应状态：TIMEOUT + has_entered_band=False

    【曲线 3】理想响应 (完美稳定)
    - 表现特征：温度快速、平滑地爬升至目标带，无超调（或微小超调），并迅速满足连续稳定时间 (stable_duration) 退出。
    - 物理意义：当前 PID 参数搭配绝佳，系统的阻尼比极度接近临界阻尼 (最佳响应)。
    - 应对策略：[完成] 测试提前判定成功！可交由 LLM 评估是否还能进一步压榨上升时间(Rise Time)。
    - 对应状态：STABLE

    【曲线 4】持续震荡 (极限环震荡不收敛)
    - 表现特征：进入目标带后，围绕设定值做等幅或发散的持续震荡，直到超时都无法停歇。
    - 物理意义：比例项(P)过大导致系统过于敏感，或积分项(I)过强引发了严重的积分饱和与相位滞后。
    - 应对策略：[LLM 精调] 识别出等幅震荡特征后可提前熔断。交由 LLM 进行大幅降 P 或加 D 的抑制操作。
    - 对应状态：LIMIT_CYCLE_OSCILLATION / TIMEOUT + 高标准差

    【曲线 5】超调后稳定 (衰减震荡)
    - 表现特征：冲过设定值（明显超调），但经过几次上下波动的衰减震荡后，最终能够收敛并稳定在目标带内。
    - 物理意义：比例项(P)略微偏大，或者微分项(D)的阻尼抑制力不足，但系统整体是稳定的。
    - 应对策略：[LLM 精调] 属于可接受范围，但非最优。交由 LLM 分析，通常需要增大 D 来压制冲顶，或微降 P/I。
    - 对应状态：STABLE (但带有较大的 overshoot_percent)

    【曲线 6】未达标静态误差 (门外趴平 / 差一口气)
    - 表现特征：温度爬升到了目标带的下边缘附近，但【从未进入过目标带】，就在带外趴平卡死了。
    - 物理意义：P 的输出具备一定能力，但最后的冲刺动力不足，恰好与高温区的热损耗持平，缺少 I 项来抹平最后几度的误差。
    - 应对策略：[启发式旁路/LLM] 此时距离目标已近，代码可微增 P 试探，或交给 LLM 稳步引入积分项(I)来消除静差。
    - 对应状态：OUT_BAND_SSE_STUCK

    【曲线 7】达标后稳态误差 (门内失守 / 震荡后落偏)
    - 表现特征：曾经冲进过目标带（甚至发生了超调），但在系统衰减回落后，最终稳定在了目标带之外（存在静态误差）。
    - 物理意义：系统绝对具备到达目标的能力（P足够大），但因为热惯性或 I 调节不到位，导致稳态点发生了偏移。
    - 应对策略：[LLM 精调] 极其关键！绝对不能再大幅加 P（会引发曲线 4 震荡）。必须交给 LLM，依靠累积积分项(I)来精细吃掉这最后的偏差。
    - 对应状态：IN_BAND_SSE_STUCK / CONVERGING_OSCILLATION
    =========================================================================================
    """
    if not times or not inputs or len(times) < 5:
        return None
        
    time_arr = np.array(times)
    temp_arr = np.array(inputs)
    
    # --- 基础指标计算 ---
    max_temp = np.max(temp_arr)
    min_temp = np.min(temp_arr)
    overshoot = max(0.0, max_temp - setpoint)
    overshoot_percent = (overshoot / max(1.0, setpoint - start_temp)) * 100.0 if (setpoint - start_temp) > 0 else 0
    
    threshold = start_temp + (setpoint - start_temp) * 0.9
    rise_indices = np.where(temp_arr >= threshold)[0]
    rise_time = (time_arr[rise_indices[0]] - time_arr[0]) if len(rise_indices) > 0 else None
    hit_target_indices = np.where(temp_arr >= setpoint)[0]
    if len(hit_target_indices) > 0:
        first_hit_time = time_arr[hit_target_indices[0]]
        after_hit_temps = temp_arr[time_arr >= first_hit_time]
        
        # 找触碰目标后的最低点，看跌破了多少
        undershoot = max(0.0, setpoint - np.min(after_hit_temps))
    else:
        # 如果连 100% 都还没到过，绝对不存在下冲
        undershoot = 0.0

    # 只要温度曾经 >= (目标值 - 稳定带)，就认为系统有能力到达目标区域
    has_entered_band = np.any(temp_arr >= (setpoint - stable_band))

    # SSE (只取最后20%的数据算均值误差)
    sse_len = max(1, int(len(inputs) * 0.2))
    sse = np.mean(np.abs(setpoint - temp_arr[-sse_len:]))



    # --- 连续稳定判定 ---
    settling_time = 0.0
    outside_band_indices = np.where(np.abs(temp_arr - setpoint) > stable_band)[0]
    
    if len(outside_band_indices) > 0:
        last_outside_idx = outside_band_indices[-1]
        if last_outside_idx + 1 < len(time_arr):
            settling_time = time_arr[last_outside_idx + 1] - time_arr[0]
            stable_duration = time_arr[-1] - time_arr[last_outside_idx + 1]
        else:
            stable_duration = 0.0
    else:
        stable_duration = time_arr[-1] - time_arr[0]
        
    is_stuck = False
    status = "UNKNOWN"
    duration_so_far = time_arr[-1] - time_arr[0]

    observed_window = stable_dur * 0.9 # 观察窗口

    slope_threshold = 0.005   # °C/s (默认 0.005 → 0.3°C/min)
    std_threshold = stable_band * 0.7 # 标准差阈值，如果标准差小于它，认为基本稳定

    if duration_so_far >= observed_window:
        window_start = time_arr[-1] - observed_window
        mask = time_arr >= window_start
        w_time = time_arr[mask]
        w_temp = temp_arr[mask]
        
        if len(w_temp) > 5:
            w_max = np.max(w_temp)
            w_min = np.min(w_temp)
            # 计算窗口内的标准差 (衡量震荡幅值)
            current_std = np.std(w_temp)
            
            # 计算窗口内的斜率 (衡量整体趋势)
            t_rel = w_time - w_time[0]
            slope, _ = np.polyfit(t_rel, w_temp, 1)
            
            error_to_setpoint = setpoint - np.mean(w_temp)

            # A. 趋势已平 (斜率极小)
            if abs(slope) <= slope_threshold:
                # 状态 A1: 趴平且无震荡 (标准差极小)
                if current_std <= std_threshold:
                    is_stuck = True
                    # 区分卡死的具体位置
                    if error_to_setpoint > (stable_band + 5.0):
                        status = "FATAL_HEATING_STUCK"       # 曲线1
                    elif error_to_setpoint > stable_band:
                        if has_entered_band:
                            status = "IN_BAND_SSE_STUCK"     # 原曲线7的一种情况：进入后掉下来趴平
                        else:
                            status = "OUT_BAND_SSE_STUCK"    # 曲线6
                    elif error_to_setpoint < -stable_band:
                        status = "OVERSHOOT_STUCK"           # 冲上去掉不下来
                    else:
                        # 如果趴平了，且就在目标带里面，不算卡死，算成功
                        is_stuck = False 
                        status = "STABLE"
                else:
                    # 状态 A2: 趋势虽平，但标准差很大，说明在做等幅震荡 (曲线4)
                    status = "LIMIT_CYCLE_OSCILLATION"
            # B. 趋势未平 (曲线仍在运动)
            else:
                # 状态 B1: 虽然斜率没平，但标准差已经在缩小，且整体在向目标靠拢，判定为震荡收敛 (新曲线7)
                # 不需要提前停止，让它继续跑，直到满足 stable_duration
                if has_entered_band and current_std <= stable_band * 1.5:
                     if max(abs(w_max - setpoint), abs(w_min - setpoint)) <= stable_band:
                         status = "STABLE" # 已经在带内微小波动了，直接给 STABLE
                     else:
                         # 只有在带外附近震荡收敛，才叫 CONVERGING_OSCILLATION
                         status = "CONVERGING_OSCILLATION"
                else:
                     status = "MOVING" # 正常的爬升或大范围震荡中

    if status == "UNKNOWN":
            if overshoot > 10:
                status = "CRITICAL_OVERSHOOT"
            elif duration_so_far < observed_window:
                status = "MOVING"
            elif sse >= 2: 
                status = "LARGE_STEADY_ERROR"
            else:
                status = "STABLE_PENDING" # 趋于稳定但时间不够

    overall_status = {
        "FATAL_HEATING_STUCK": "加热严重不足，在低温处停滞趴平",
        "OUT_BAND_SSE_STUCK": "未达标卡死：从进入过目标带，存在静态误差",
        "IN_BAND_SSE_STUCK": "达标后趴平：进入过目标带，但最终在带外停滞",
        "OVERSHOOT_STUCK": "超调且高温趴平",
        "LIMIT_CYCLE_OSCILLATION": "等幅震荡：系统进入极限环震荡",
        "CONVERGING_OSCILLATION": "震荡收敛：进入目标带后上下波动，趋势趋稳",
        "CRITICAL_OVERSHOOT": "严重超调",
        "LARGE_STEADY_ERROR": "稳态误差较大",
        "STABLE_PENDING": "正在趋于稳定...",
        "STABLE": "系统表现完美，稳定运行",
        "MOVING": "系统正在调整中..."
    }.get(status, "未知状态")

    return {
        "overshoot": overshoot,
        "undershoot": undershoot,
        "overshoot_percent": overshoot_percent,
        "max_temp": max_temp,      
        "rise_time": rise_time,        
        "settling_time": settling_time,
        "steady_state_error": sse,
        "stable_duration": stable_duration,
        "status": status,
        "overall_status": overall_status,
        "is_stuck": is_stuck,
        "has_entered_band": has_entered_band,
        "target_zone_oscillation_std": np.std(temp_arr[temp_arr >= (setpoint - stable_band * 2)]) if has_entered_band else 0 # 进入目标带后的震荡幅度
    } 