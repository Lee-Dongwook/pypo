import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class MetricLogger:
    def __init__(self, storage_dir: str = "data/trajectories", filename: str = "success_trajectories.jsonl") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.storage_dir / filename
    def log_success_trajectory(
        self,
        task_id: str,
        system_prompt: str,
        instruction: str,
        turns: List[Dict[str, Any]],
        final_code: str,
        passed_tests: List[str],
        metrics: Optional[Dict[str, Any]] = None,
    ) -> None:
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "task_id": task_id,
            "status": "SUCCESS",
            "system_prompt": system_prompt,
            "instruction": instruction,
            "turns": turns,  # 각 시도별 [prompt, output, error_feedback] 목록
            "final_code": final_code,
            "passed_tests": passed_tests,
            "metrics": metrics
            or {
                "total_iterations": len(turns),
                "ast_passed": True,
                "regression_passed": True,
            }
        }

        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

def log_evaluation_run(self, run_summary: Dict[str, Any]) -> None:
    eval_file = self.storage_dir / "evaluation_runs.jsonl"
    record = {"timestamp": datetime.utcnow().isoformat() + "Z", **run_summary}
    with open(eval_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
