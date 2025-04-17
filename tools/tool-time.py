function_schema = {
    "type": "object",
    "properties": {},
    "required": []
}
def function_call():
    from datetime import datetime
    now = datetime.now()
    return now.strftime("Il est %H:%M:%S")
