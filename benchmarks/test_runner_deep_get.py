import sys
import requests
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(root_dir))

from src.app.agents.runner import AgentRunner
from src.app.agents.evaluation.evaluator import AgentEvaluator

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
            "temperature": 0.1,
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
    except Exception as e:
        print(f"[Ollama Error]: {str(e)}")
        return ""


def test_runner_deep_get(code_string: str) -> tuple[bool, str]:
    local_namespace = {}
    try:
        exec(code_string, {}, local_namespace)
        deep_get_func = local_namespace.get("deep_get")
        
        if not deep_get_func:
            return False, "RuntimeError: 'deep_get' 함수가 정의되지 않았습니다."

        data = {"a": {"b": {"c": 42}}}
        assert deep_get_func(data, "a.b.c") == 42, f"Case 1 Failed: expected 42"

        assert deep_get_func(data, "a.b.x", default="N/A") == "N/A", f"Case 2 Failed: expected 'N/A'"

        data_with_none = {"a": {"b": None}}
        assert deep_get_func(data_with_none, "a.b.c", default="safe") == "safe", f"Case 3 Failed: expected 'safe'"

        return True, ""

    except AssertionError as ae:
        return False, f"AssertionError: {str(ae)}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)} (중간 경로가 None이거나 dict가 아닐 때의 예외 처리를 보완하세요)"

def main():
    print("=" * 50)
    print("Retry Loop Benchmark: deep_get Edge Case Test")
    print("=" * 50)

    runner = AgentRunner(max_iterations=3)
    evaluator = AgentEvaluator()

    task_id = "deep_get_edge_case_01"
    system_prompt = (
        "너는 탁월한 Python 소프트웨어 엔지니어이다. "
        "주어진 요구사항과 테스트 실패 에러 로그를 분석하여, 엣지 케이스(중간 값이 None인 경우 등)를 "
        "완벽하게 방어하는 견고한 파이썬 함수 코드만 작성하라."
    )
    instruction = (
        "deep_get(data, path, default=None) 함수를 구현하시오. "
        "path는 'a.b.c' 형태이며, 중간에 None이 있거나 키가 없을 때 예외 없이 안전하게 default를 반환해야 합니다."
    )

    success = runner.run_task(
        task_id=task_id,
        system_prompt=system_prompt,
        instruction=instruction,
        generator_func=ollama_qwen_generator,
        test_runner_func=test_runner_deep_get,
    )

    if success:
        print(f"\n[CLI] 복잡한 버그 태스크 '{task_id}' Self-Correction 성공 완료!")
    else:
        print(f"\n[CLI] 태스크 '{task_id}' 최종 실패.")

    print("\n")
    evaluator.print_evaluation_report(total_benchmark_tasks=1)


if __name__ == "__main__":
    main()
