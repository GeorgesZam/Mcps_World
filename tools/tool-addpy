# tool/tool-add.py

# Schema definition for the addition tool
function_schema = {
    "type": "object",
    "properties": {
        "number1": {
            "type": "number",
            "description": "The first number to add"
        },
        "number2": {
            "type": "number", 
            "description": "The second number to add"
        }
    },
    "required": ["number1", "number2"]
}

def function_call(number1: float, number2: float) -> float:
    """
    Adds two numbers together and returns the result.
    
    Args:
        number1: First number to add
        number2: Second number to add
        
    Returns:
        The sum of number1 and number2
    """
    return int(number1) + int(number2)
