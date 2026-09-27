from typing import Any, Dict
from pydantic import ValidationError
from tools import TOOL_REGISTRY

ROLE_PERMISSIONS = {
    "customer": {
        "list_all_products",
        "search_products",
        "check_stock",
        "buy_product",
    },
    "admin": {
        "list_all_products",
        "search_products",
        "check_stock",
        "buy_product",
        "delete_product",
    },
}


class SafetyHarness:
    def __init__(self, role: str = "customer", max_iterations: int = 5):
        self.role = role.lower()
        self.max_iterations = max_iterations
        self.iteration_count = 0

    def reset_limit(self):
        """Resets the counter for every new question in the chat loop."""
        self.iteration_count = 0

    def check_loop_limit(self) -> bool:
        self.iteration_count += 1
        return self.iteration_count <= self.max_iterations

    def execute_safely(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        allowed = ROLE_PERMISSIONS.get(self.role, set())
        if tool_name not in allowed:
            return (
                f"PERMISSION DENIED: Active role '{self.role.upper()}' is not "
                f"authorized to execute '{tool_name}'."
            )

        tool_obj = TOOL_REGISTRY.get(tool_name)
        if not tool_obj:
            return f"SYSTEM ERROR: Tool '{tool_name}' is not registered."

        try:
            result = tool_obj.invoke(tool_args)
            return str(result)
        except ValidationError as ve:
            return f"INPUT VALIDATION REJECTION: {ve}"
        except Exception as e:
            return f"DATABASE/RUNTIME ERROR: {str(e)}"