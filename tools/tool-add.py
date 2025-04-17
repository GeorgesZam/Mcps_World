def function_call(number1: float, number2: float):
    return number1 + number2

function_schema = {
    "name": "add",
    "description": "Additionne deux nombres.",
    "type": "object",
    "properties": {
        "number1": {"type": "number", "description": "Premier nombre"},
        "number2": {"type": "number", "description": "Second nombre"}
    },
    "required": ["number1", "number2"],
}
