def function_call(a: float, b: float) -> float:
    return float(a) + float(b)

matcher = lambda prompt: "addition" in prompt or "add" in prompt or "+" in prompt
__doc__ = "Addition de deux nombres, usage: addition a=2 b=3"
