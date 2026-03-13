'''In memory query history store (no db needed)'''

from datetime import datetime

# In-memory store — resets on server restart
_history = []
_max_history = 100


def add_entry(question: str, sql: str, success: bool, row_count: int = 0, error: str = None):
    entry = {
        "id": len(_history) + 1,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "question": question,
        "sql": sql,
        "success": success,
        "row_count": row_count,
        "error": error
    }
    _history.append(entry)

    # Keep only last N entries
    if len(_history) > _max_history:
        _history.pop(0)

    return entry


def get_history():
    return list(reversed(_history))  # Most recent first


def clear_history():
    global _history
    _history = []
    return {"cleared": True}