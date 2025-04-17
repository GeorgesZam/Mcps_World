def function_call(a: float, b: float) -> float:
    return a + b

function_schema = {
    "name": "add",
    "description": "Addition de 2 nombres",
    "type": "object",
    "properties": {
        "a": {"type": "number", "description": "Nombre 1"},
        "b": {"type": "number", "description": "Nombre 2"},
    },
    "required": ["a", "b"]
}
