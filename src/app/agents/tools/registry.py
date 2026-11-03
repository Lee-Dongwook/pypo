import inspect
from typing import Callable, Dict, Any

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.schemas: list[dict] = []
    
    def register(self, name: str, description: str):
        def decorator(func: Callable):
            self.tools[name] = func
            sig = inspect.signature(func)
            self.schemas.append({
                "name": name,
                "description": description,
                "signature": str(sig)
            })
            return func
        return decorator
    
    def execute(self, name: str, kwargs: dict) -> Any:
        if name not in self.tools:
            return f"Error: Tool '{name}' not found."
        try:
            return self.tools[name](**kwargs)
        except Exception as e:
            return f"Tool Execution Error ({type(e).__name__}): {str(e)}"

tool_registry = ToolRegistry()
