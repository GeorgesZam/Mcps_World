{
    "name": "get_current_time",
    "description": "Get the current time in a specific timezone",
    "parameters": {
        "type": "object",
        "properties": {
            "timezone": {
                "type": "string",
                "description": "Timezone like Europe/Paris, America/New_York etc.",
                "default": "local"
            },
            "format": {
                "type": "string",
                "description": "Time format string",
                "default": "%Y-%m-%d %H:%M:%S"
            }
        }
    },
    "function": "def get_current_time(timezone='local', format='%Y-%m-%d %H:%M:%S'):\n    if timezone == 'local':\n        current_time = datetime.now()\n    else:\n        tz = pytz.timezone(timezone)\n        current_time = datetime.now(tz)\n    return {\n        'time': current_time.strftime(format),\n        'timezone': timezone if timezone != 'local' else 'local time',\n        'timestamp': current_time.timestamp()\n    }"
}
