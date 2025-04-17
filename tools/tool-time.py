## tool/tool-time.py
from datetime import datetime


def function_call():
    """Return the actual time"""
    now = datetime.now()
    return now.strftime("Il est %H:%M:%S")
