import ast
from typing import List, Tuple


class _ConventionVisitor(ast.NodeVisitor):
    def __init__(self, forbidden_nodes: List[str]) -> None:
        self.forbidden_nodes = forbidden_nodes
        self.violations: List[str] = []
    
    def visit_Global(self, node: ast.Global) -> None:
        self.violations.append("전역 변수(global) 선언은 허용되지 않습니다.")
        self.generic_visit(node)
    
    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            self.violations.append(f"보안 위험: '{node.func.id}()' 함수 사용이 금지되어 있습니다.")
        self.generic_visit(node)
    

class ASTGatekeeper:
    def __init__(self, forbidden_nodes: List[str] = None) -> None:
        self.forbidden_nodes = forbidden_nodes or []
    
    def validate_code(self, code_string: str) -> Tuple[bool, str]:
        if not code_string or not code_string.strip():
            return False, "ASTError: 코드가 비어 있음."
        
        try:
            tree = ast.parse(code_string)
        except SyntaxError as e:
            error_msg = f"SyntaxError: {e.msg} at line {e.lineno}"
            return False, error_msg
        except Exception as e:
            return False, f"ASTParsingError: {str(e)}"
        
        visitor = _ConventionVisitor(self.forbidden_nodes)
        visitor.visit(tree)

        if visitor.violations:
            violation_str = ", ".join(visitor.violations)
            return False, f"ConventionViolation: {violation_str}"

        return True, "AST Validation Passed"


