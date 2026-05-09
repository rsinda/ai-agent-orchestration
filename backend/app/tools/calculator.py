import ast
import math
import operator
from typing import Any

from backend.app.tools.base import RuntimeTool, ToolResult, ToolSpec


class CalculatorTool(RuntimeTool):
    spec = ToolSpec(
        name="calculator",
        description="Safely evaluate arithmetic expressions for calculations.",
        input_schema={
            "type": "object",
            "properties": {"expression": {"type": "string"}},
            "required": ["expression"],
        },
    )

    operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }
    unary_operators = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }
    functions = {
        "abs": abs,
        "ceil": math.ceil,
        "cos": math.cos,
        "floor": math.floor,
        "log": math.log,
        "max": max,
        "min": min,
        "pow": pow,
        "round": round,
        "sin": math.sin,
        "sqrt": math.sqrt,
        "tan": math.tan,
    }
    constants = {
        "e": math.e,
        "pi": math.pi,
    }

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        expression = str(arguments.get("expression", "")).strip()
        if not expression:
            raise ValueError("calculator requires an expression.")
        result = self._evaluate(expression)
        return ToolResult(content=f"{expression} = {result}", data={"expression": expression, "result": result})

    def _evaluate(self, expression: str) -> float | int:
        tree = ast.parse(expression, mode="eval")
        return self._eval_node(tree.body)

    def _eval_node(self, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name) and node.id in self.constants:
            return self.constants[node.id]
        if isinstance(node, ast.BinOp) and type(node.op) in self.operators:
            return self.operators[type(node.op)](self._eval_node(node.left), self._eval_node(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in self.unary_operators:
            return self.unary_operators[type(node.op)](self._eval_node(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in self.functions:
            args = [self._eval_node(arg) for arg in node.args]
            return self.functions[node.func.id](*args)
        raise ValueError("Expression contains unsupported syntax.")

