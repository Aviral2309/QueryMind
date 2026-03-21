from datetime import datetime

_history    = []
_max_history = 100


def add_entry(question, sql, success, row_count=0, error=None):
    entry = {
        "id":        len(_history) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question":  question,
        "sql":       sql,
        "success":   success,
        "row_count": row_count,
        "error":     error
    }
    _history.append(entry)
    if len(_history) > _max_history:
        _history.pop(0)
    return entry


def get_history():
    return list(reversed(_history))


def clear_history():
    global _history
    _history = []
    return {"cleared": True}