from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from .evaluation.metric_logger import MetricLogger
from .validators.ast_gate import ASTGatekeeper


class AgentRunner:
    def __init__(
        self,
        max_iterations: int = 3,
        mistakes_file_path: str = "data/mistakes.md",
        trajectory_dir: str = "data/trajectories",
    ) -> None:
        self.max_iterations = max_iterations
        self.mistakes_file = Path(mistakes_file_path)
        self.ast_gate = ASTGatekeeper()
        self.logger = MetricLogger(storage_dir=trajectory_dir)

    def _load_mistakes(self) -> str:
        if not self.mistakes_file.exists():
            return ""
        try:
            return self.mistakes_file.read_text(encoding="utf-8")
        except Exception:
            return ""

    def _append_mistake(self, problem: str, solution: str) -> None:
        self.mistakes_file.parent.mkdir(parents=True, exist_ok=True)
        
        entries = []
        if self.mistakes_file.exists():
            content = self.mistakes_file.read_text(encoding="utf-8")
            entries = [e.strip() for e in content.split("---") if e.strip()]

        new_entry = f"**문제(Problem):** {problem}\n**해결(Solution):** {solution}"
        entries.append(new_entry)

        # 최대 50개 유지 (슬라이딩 윈도우)
        if len(entries) > 50:
            entries = entries[-50:]

        self.mistakes_file.write_text("\n---\n".join(entries), encoding="utf-8")

    def run_task(
        self,
        task_id: str,
        system_prompt: str,
        instruction: str,
        generator_func: Callable[[str, str], str],
        test_runner_func: Callable[[str], Tuple[bool, str]],
    ) -> bool:
        turns: List[Dict[str, Any]] = []
        current_feedback = ""
        mistakes_context = self._load_mistakes()

        enhanced_system_prompt = system_prompt
        if mistakes_context:
            enhanced_system_prompt += f"\n\n### [Previous Mistakes & Solutions]\n{mistakes_context}"
        
        success = False
        final_code = ""

        for attempt in range(1, self.max_iterations + 1):
            print(f"[Task: {task_id}] Iteration {attempt} of {self.max_iterations}....")

            generated_code = generator_func(enhanced_system_prompt, instruction)

            turn_record = {
                "attempt": attempt,
                "prompt": instruction if attempt == 1 else current_feedback,
                "output": generated_code,
                "error_feedback": None,
            }

            ast_passed, ast_msg = self.ast_gate.validate_code(generated_code)
            if not ast_passed:
                print(f"AST 정적 분석 실패: {ast_msg}")
                current_feedback = f"AST Error: {ast_msg}. 코드를 수정하여 다시 작성해주세요."
                turn_record["error_feedback"] = current_feedback
                turns.append(turn_record)
                continue
            
            test_passed, test_error_log = test_runner_func(generated_code)
            if not test_passed:
                print(f"테스트/런타임 실패: {test_error_log[:100]}...")
                current_feedback = f"Runtime/Test Error:\n{test_error_log}\n위 에러를 해결하도록 코드를 고쳐주세요."
                turn_record["error_feedback"] = current_feedback
                turns.append(turn_record)
                continue
            
            print(f"[Task: {task_id}] 이터레이션 성공 완료!")
            final_code = generated_code
            turns.append(turn_record)
            success = True
            break
            
        if success:
            self.logger.log_success_trajectory(
                task_id=task_id,
                system_prompt=system_prompt,
                instruction=instruction,
                turns=turns,
                final_code=final_code,
                passed_tests=[task_id],
                metrics={"total_iterations": len(turns), "ast_passed": True, "regression_passed": True},
            )
        else:
            print(f"[Task: {task_id}] 최대 이터레이션({self.max_iterations}회) 초과로 실패 처리되었습니다.")
        
        return success

