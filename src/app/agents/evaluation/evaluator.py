import json
from pathlib import Path
from typing import Any, Dict, List

class AgentEvaluator:
    def __init__(self, storage_dir: str = "data/trajectories") -> None:
        self.storage_dir = Path(storage_dir)
        self.success_file = self.storage_dir / "success_trajectories.jsonl"
        self.eval_runs_file = self.storage_dir / "evaluation_runs.jsonl"
    
    def load_success_trajectories(self) -> List[Dict[str, Any]]:
        if not self.success_file.exists():
            return []
        
        trajectories = []
        with open(self.success_file,  "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        trajectories.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return trajectories

    def compute_metrics(self, total_benchmark_tasks: int = None) -> Dict[str, Any]:
        trajectories = self.load_success_trajectories()
        total_successes = len(trajectories)

        if total_successes == 0:
            return {
                "total_tasks": 0,
                "total_successes": 0,
                "pass_at_1_rate": 0.0,
                "retry_success_rate": 0.0,
                "avg_iterations": 0.0,
                "regression_rate": 0.0,
                "ast_rejection_rate": 0.0,
            }

        pass_at_1_count = 0
        retry_success_count = 0
        total_iterations = 0
        regression_failures = 0
        ast_rejections = 0

        for item in trajectories:
            turns = item.get("turns", [])
            iterations = len(turns)
            total_iterations += iterations

            if iterations == 1:
                pass_at_1_count += 1
            else:
                retry_success_count += 1
            
            metrics = item.get("metrics", {})
            if not metrics.get("regression_passed", True):
                regression_failures += 1
            if not metrics.get("ast_passed", True):
                ast_rejections += 1

        base_tasks = total_benchmark_tasks if total_benchmark_tasks and total_benchmark_tasks >= total_successes else total_successes

        return {
            "total_evaluated_tasks": base_tasks,
            "total_successes": total_successes,
            "pass_at_1_rate": (pass_at_1_count / base_tasks) * 100,
            "retry_success_rate": (retry_success_count / base_tasks) * 100,
            "avg_iterations": total_iterations / total_successes,
            "regression_rate": (regression_failures / total_successes) * 100,
            "ast_rejection_rate": (ast_rejections / total_successes) * 100,
        }
    
    def print_evaluation_report(self, total_benchmark_tasks: int = None) -> None:
        metrics = self.compute_metrics(total_benchmark_tasks)

        print("=" * 50)
        print(" Self-Evolving Code Agent - Evaluation Dashboard")
        print("=" * 50)
        print(f" • 총 평가 대상 태스크: {metrics['total_evaluated_tasks']}개")
        print(f" • 성공 완료 태스크:   {metrics['total_successes']}개")
        print("-" * 50)
        print(f" [1] Pass@1 (1차 성공률):       {metrics['pass_at_1_rate']:.1f}%")
        print(f" [2] Retry Success (재시도 성공률): {metrics['retry_success_rate']:.1f}%")
        print(f" [3] 평균 시도 이터레이션:        {metrics['avg_iterations']:.2f}회 / 성공")
        print(f" [4] 회귀율 (Regression Rate):  {metrics['regression_rate']:.1f}%")
        print(f" [5] AST 정적분석 차단율:       {metrics['ast_rejection_rate']:.1f}%")
        print("=" * 50)

if __name__ == "__main__":
    evaluator = AgentEvaluator()
    evaluator.print_evaluation_report()
