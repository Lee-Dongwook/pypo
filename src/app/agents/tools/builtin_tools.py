from .registry import tool_registry
from ..validators.ast_gate import validate_ast

@tool_registry.register("run_python_test", "파이썬 코드를 받아 샌드박스 네임스페이스에서 실행하고 단위 테스트 결과를 반환합니다.")
def run_python_test(code_string: str) -> str:
    is_valid, err = validate_ast(code_string)
    if not is_valid:
        return f"AST Verification Failed: {err}"
    
    local_ns = {}
    try:
        exec(code_string, {}, local_ns)
        return "Success: Code executed without syntax or runtime errors."
    except Exception as e:
        return f"Test Execution Failed: {type(e).__name__}: {str(e)}"

        
