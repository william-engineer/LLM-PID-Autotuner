import json
import re
from typing import Optional, Dict, Any
import logging

class LLMTuner:
    def __init__(self, api_key: str, base_url: str, model: str, provider: str = "openai"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.provider = provider

        try:
            if self.provider == "openai":
                import openai
                self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            import requests
            self.requests = requests

    
    def parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        text = re.sub(r'```(?:json)?\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try: return json.loads(match.group())
            except: pass
        return None

    def analyze(self, prompt_data: dict, history_text: str, system_prompt: str) -> Optional[Dict[str, Any]]:
        """
        调用 LLM 分析当前测试结果并给出下一轮 PID 参数建议
        """
        prompt_data_str = "## 本轮回合测试结果:\n" + json.dumps(prompt_data, indent=2, ensure_ascii=False)
        user_prompt = f"{history_text}\n\n{prompt_data_str}\n\n请分析并给出下一轮参数。务必返回 JSON。"
        try:
            if self.provider == "openai":
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                    temperature=0.2
                )
                return self.parse_json(resp.choices[0].message.content)
        except Exception as e:
            logging.error(f"LLM API Error: {e}")

    def test_connection(self) -> tuple[bool, str]:
        """
        测试大模型 API 连通性
        """
        try:
            if self.provider == "openai":
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=20
                )
                reply_text = resp.choices[0].message.content.strip()
                return True, f"API Connection Successful! Model reply: '{reply_text}'"
        except Exception as e:
            logging.error(f"Connection Failed: {str(e)}")
            return False, f"Connection Failed: {str(e)}"