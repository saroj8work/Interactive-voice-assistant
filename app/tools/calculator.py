"""
Safe Mathematical Calculation Tool.
Evaluates expressions using Python's AST parser without dangerous arbitrary code execution.
"""
import ast
import operator
import math
from app.tools.base import BaseTool, ToolResult

# Allowed operators
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "abs": abs,
    "round": round,
    "pi": math.pi,
    "e": math.e,
}


class SafeMathEvaluator:
    @classmethod
    def evaluate(cls, expression: str) -> float:
        # Normalize expression
        expr = expression.replace("^", "**").replace("x", "*").replace("X", "*")
        node = ast.parse(expr, mode="eval").body
        return cls._eval_node(node)

    @classmethod
    def _eval_node(cls, node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Unsupported constant type: {type(node.value)}")

        if isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported operator: {op_type}")
            left = cls._eval_node(node.left)
            right = cls._eval_node(node.right)
            return SAFE_OPERATORS[op_type](left, right)

        if isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in SAFE_OPERATORS:
                raise ValueError(f"Unsupported unary operator: {op_type}")
            operand = cls._eval_node(node.operand)
            return SAFE_OPERATORS[op_type](operand)

        if isinstance(node, ast.Call):
            func_name = getattr(node.func, "id", None)
            if func_name not in SAFE_FUNCTIONS:
                raise ValueError(f"Function '{func_name}' is not permitted")
            args = [cls._eval_node(arg) for arg in node.args]
            return SAFE_FUNCTIONS[func_name](*args)

        if isinstance(node, ast.Name):
            if node.id in SAFE_FUNCTIONS:
                return SAFE_FUNCTIONS[node.id]
            raise ValueError(f"Variable '{node.id}' is not permitted")

        raise ValueError(f"Unsupported AST node: {type(node).__name__}")


class CalculatorTool(BaseTool):
    name = "calculator"
    description = "Evaluates mathematical expressions, percentages, and arithmetic operations safely."
    parameters_schema = {
        "expression": {"type": "string", "description": "Math expression (e.g. '12 * 8', '(15 / 100) * 85')"}
    }

    def execute(self, expression: str, **kwargs) -> ToolResult:
        try:
            val = SafeMathEvaluator.evaluate(expression)
            # Format cleanly
            if isinstance(val, float) and val.is_integer():
                formatted_val = int(val)
            else:
                formatted_val = round(val, 4)

            return ToolResult(
                success=True,
                data={"expression": expression, "result": formatted_val},
                message=f"Calculation result for '{expression}' is {formatted_val}."
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Calculation failed: {str(e)}",
                message=f"I couldn't calculate that: {str(e)}"
            )
