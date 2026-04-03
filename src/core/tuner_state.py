from collections import deque
from typing import Dict, Any

class TuningHistoryManager:
    def __init__(self, max_history: int = 5):
        self.history = deque(maxlen=max_history)
    
    def add_record(self, round_num: int, pid: Dict[str, float], metrics: Dict[str, Any], overall_status: str, analysis: str):
        self.history.append({
            "round": round_num,
            "pid": pid,
            "metrics": metrics,
            "overall_status": overall_status,
            "analysis": analysis
        })
    
    def to_prompt_text(self) -> str:
        if not self.history:
            return "## 调参历史: 无 (这是第一轮测试)"
        text = "## 调参历史 (最近几轮):\n"
        for rec in self.history:
            m = rec['metrics']
            pid = rec['pid']
            text += (f"- Round {rec['round']}: P={pid['p']:.4f}, I={pid['i']:.4f}, D={pid['d']:.4f} "
                     f"-> 超调={m.get('overshoot',0):.1f}, 稳态误差={m.get('steady_state_error',0):.2f}, "
                     f"状态={rec['overall_status']}\n")
        return text