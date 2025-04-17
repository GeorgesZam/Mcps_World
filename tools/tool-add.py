# tools/tool-add.py

def function_call(a: float, b: float) -> float:
    """
    Additionne deux nombres.
    """
    return a + b

function_schema = {
    "name": "addition",
    "description": "Additionne deux nombres a et b.",
    "type": "object",
    "properties": {
        "a": {
            "type": "number",
            "description": "Premier nombre à additionner"
        },
        "b": {
            "type": "number",
            "description": "Deuxième nombre à additionner"
        }
    },
    "required": ["a", "b"]
}
