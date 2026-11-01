import sys
import requests
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from src.app.agents.runner import AgentRunner
from src.app.agents.evaluation.evaluator import AgentEvaluator

def mock_llm_generator(system_prompt: str, instruction: str) -> str:
    """테스트를 위해 시뮬레이션된 LLM 응답 생성기."""
    if "Runtime/Test Error" in instruction or "에러를 해결" in instruction or "AssertionError" in instruction:
        return "def add_numbers(a: int, b: int) -> int:\n    return a + b\n"
    else:
        return "def add_numbers(a: int, b: int) -> int:\n    return a - b\n"

def mock_test_runner(code_string: str) -> tuple[bool, str]:
    """생성된 코드를 안전한 네임스페이스에서 실행하고 단위 테스트를 검증합니다."""
    local_namespace = {}
    try:
        exec(code_string, {}, local_namespace)
        add_func = local_namespace.get("add_numbers")
        
        if not add_func:
            return False, "RuntimeError: 'add_numbers' 함수가 정의되지 않았습니다."

        result = add_func(3, 5)
        if result == 8:
            return True, ""
        else:
            return False, f"AssertionError: add_numbers(3, 5) returned {result}, expected 8"

    except Exception as e:
        return False, f"ExecutionException: {str(e)}"

def ollama_qwen_generator(system_prompt: str, instruction: str) -> str:
    url = "http://localhost:11434/api/generate"

    full_prompt = (
        f"{system_prompt}\n\n"
        f"### Request/Feedback:\n{instruction}\n\n"
        "Rules:\n"
        "1. 오직 실행 가능한 파이썬 코드만 작성하세요.\n"
        "2. 마크다운 코드블록 백틱(```python 등)을 절대 포함하지 말고, 순수 코드 문자열만 출력하세요."
    )

    payload = {
        "model": "qwen2.5-coder:7b",
        "prompt": full_prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # 7B 모델 환각 방지 및 결정론적 출력 유도
            "num_predict": 1024,
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        raw_code = result.get("response", "").strip()

        if raw_code.startswith("```"):
            lines = raw_code.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_code = "\n".join(lines).strip()

        return raw_code

    except requests.exceptions.ConnectionError:
        print("[Ollama Error] 로컬 Ollama 서버에 연결할 수 없습니다. 'ollama serve'가 실행 중인지 확인하세요.")
        sys.exit(1)
    except Exception as e:
        print(f"[Ollama Error] API 호출 중 오류 발생: {str(e)}")
        return ""

def main():
    print("=" * 50)
    print(" Self-Evolving Agent CLI Benchmark Test Runner")
    print("=" * 50)

    runner = AgentRunner(max_iterations=3)
    evaluator = AgentEvaluator()

    task_id = "math_add_test_01"
    system_prompt = "너는 탁월한 Python 소프트웨어 엔지니어이다. 주어진 요구사항에 맞춰 정확한 코드를 작성하라."
    instruction = "add_numbers(a, b) 함수가 올바르게 두 숫자의 합을 반환하도록 구현하시오."

    success = runner.run_task(
        task_id=task_id,
        system_prompt=system_prompt,
        instruction=instruction,
        generator_func=ollama_qwen_generator,
        test_runner_func=mock_test_runner,
    )

    if success:
        print(f"\n[CLI] 태스크 '{task_id}' 성공적으로 완료 및 궤적 저장 완료!")
    else:
        print(f"\n[CLI] 태스크 '{task_id}' 최종 실패.")

    print("\n")
    evaluator.print_evaluation_report(total_benchmark_tasks=1)


if __name__ == "__main__":
    main()
