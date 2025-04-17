function_schema = {
    "type": "object",
    "properties": {},
    "required": [],
    "triggers": ["secret", "nombre secret", "nombre magique", "secret number"],
    "description": "Donner un nombre secret mystère."
}
def function_call():
    from datetime import datetime
    now = datetime.now()
    return now.strftime("Il est %H:%M:%S")
