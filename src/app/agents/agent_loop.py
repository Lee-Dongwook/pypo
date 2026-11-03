import json
import requests

from .tools.registry import tool_registry

class AgentLoop:
    def __init__(self, max_steps: int = 5):
        self.max_steps = max_steps
        self.url = "http://localhost:11434/api/generate"
    
    def run(self, task_description: str):
        print(f"[AgentLoop] Starting Task: {task_description}")
        
        tools_desc = json.dumps(tool_registry.schemas, indent=2, ensure_ascii=False)
        system_prompt = (
            "너는 자율형 AI 엔지니어 에이전트이다. 주어진 목표를 달성하기 위해 아래 도구들을 활용해라.\n"
            f"Available Tools:\n{tools_desc}\n\n"
            "반드시 다음 JSON 형식으로만 응답하라:\n"
            "{\n  \"thought\": \"현재 상황에 대한 분석 및 다음 행동 계획\",\n  \"action\": \"도구이름 또는 finish\",\n  \"action_input\": { \"인자이름\": \"값\" }\n}"
        )

        conversation_history = f"Task: {task_description}\n"

        for step in range(1, self.max_steps + 1):
            print(f"\n--- Step {step} / {self.max_steps} ---")
            
            prompt = f"{system_prompt}\n\nHistory:\n{conversation_history}\nResponse:"
            
            payload = {
                "model": "qwen2.5-coder:7b",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 1024}
            }

            response = requests.post(self.url, json=payload, timeout=60)
            raw_response = response.json().get("response", "").strip()

            try:
                cleaned = raw_response.replace("```json", "").replace("```", "").strip()
                res_json = json.loads(cleaned)
            except json.JSONDecodeError:
                print(f"JSON Parse Error. Raw Output:\n{raw_response}")
                conversation_history += f"\nStep {step} Error: Invalid JSON response format."
                continue

            thought = res_json.get("thought", "")
            action = res_json.get("action", "")
            action_input = res_json.get("action_input", {})

            print(f"Thought: {thought}")
            print(f"Action: {action} | Input: {action_input}")

            if action == "finish":
                print("에이전트가 태스크 완료를 선언했습니다.")
                return True

            observation = tool_registry.execute(action, action_input)
            print(f"Observation: {observation}")

            conversation_history += f"\nStep {step} - Thought: {thought}\nAction: {action}({action_input})\nObservation: {observation}\n"

        print("최대 스텝 초과로 에이전트 루프가 종료되었습니다.")
        return False
