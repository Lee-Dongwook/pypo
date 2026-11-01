# benchmarks/test_runner_retry_forced.py
import sys
from pathlib import Path

import requests

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from src.app.agents.evaluation.evaluator import AgentEvaluator  # noqa: E402
from src.app.agents.runner import AgentRunner  # noqa: E402

_ATTEMPT_COUNTER = 0

def forced_retry_llm_generator(system_prompt: str, instruction: str) -> str:
    global _ATTEMPT_COUNTER
    _ATTEMPT_COUNTER += 1

    url = "http://localhost:11434/api/generate"
    
    if _ATTEMPT_COUNTER == 1:
        print("💡 [Mock Injection] 1차 시도: 의도적으로 실패하는 오답 코드를 생성합니다.")
        forced_instruction = instruction + "\n\n[Constraint]: 의도적으로 테스트를 실패하는 버그(예: 결과값에 무조건 +1을 더하거나 잘못된 연산)를 포함해서 코드를 작성하세요."
    else:
        print(f"💡 [Mock Injection] {_ATTEMPT_COUNTER}차 시도: 에러 피드백을 반영하여 정상 코드를 생성합니다.")
        forced_instruction = instruction + f"\n\n[Feedback Applied]: 이전 시도에서 테스트가 실패했습니다. 에러를 분석하여 완벽하게 작동하는 코드를 작성하세요. (지시사항: {instruction})"

    full_prompt = (
        f"{system_prompt}\n\n"
        f"### Request:\n{forced_instruction}\n\n"
        "Rules:\n"
        "1. 오직 실행 가능한 파이썬 코드만 작성하세요.\n"
        "2. 마크다운 코드블록 백틱(```python 등)을 절대 포함하지 마세요."
    )

    payload = {
        "model": "qwen2.5-coder:7b",
        "prompt": full_prompt,
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1024}
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        raw_code = response.json().get("response", "").strip()

        if raw_code.startswith("```"):
            lines = raw_code.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_code = "\n".join(lines).strip()

        return raw_code
    except Exception as e:
        print(f"[Ollama Error]: {str(e)}")
        return ""


def test_runner_multiplier(code_string: str) -> tuple[bool, str]:
    local_namespace = {}
    try:
        exec(code_string, {}, local_namespace)
        func = local_namespace.get("multiply_values")
        
        if not func:
            return False, "RuntimeError: 'multiply_values' 함수가 정의되지 않았습니다."

        res = func(4, 5)
        if res == 20:
            return True, ""
        else:
            return False, f"AssertionError: multiply_values(4, 5) returned {res}, expected 20"

    except Exception as e:
        return False, f"ExecutionException: {str(e)}"


def main():
    global _ATTEMPT_COUNTER
    _ATTEMPT_COUNTER = 0

    print("=" * 50)
    print("Forced Retry Loop Benchmark Test")
    print("=" * 50)

    runner = AgentRunner(max_iterations=3)
    evaluator = AgentEvaluator()

    task_id = "forced_retry_test_01"
    system_prompt = "너는 탁월한 Python 소프트웨어 엔지니어이다. 요구사항에 맞는 파이썬 함수를 작성하라."
    instruction = "multiply_values(a, b) 함수를 구현하시오. 두 매개변수의 곱(a * b)을 반환해야 합니다."

    success = runner.run_task(
        task_id=task_id,
        system_prompt=system_prompt,
        instruction=instruction,
        generator_func=forced_retry_llm_generator,
        test_runner_func=test_runner_multiplier,
    )

    if success:
        print(f"\n[CLI] 강제 Retry 태스크 '{task_id}' Self-Correction 성공 완료!")
    else:
        print(f"\n[CLI] 태스크 '{task_id}' 최종 실패.")

    print("\n")
    evaluator.print_evaluation_report(total_benchmark_tasks=3)


if __name__ == "__main__":
    main()
