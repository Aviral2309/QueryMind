'''Executes SQL against the connected DB and returns results.'''

from db_connector import get_db
import re


def execute_query(sql: str) -> dict:
    """
    Executes a SQL query and returns rows + columns.
    Returns {"success": True, "columns": [...], "rows": [...]}
    or      {"success": False, "error": "..."}
    """
    try:
        db = get_db()

        # Use LangChain's run method to execute
        # But we need raw results, so use _engine directly
        with db._engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text(sql))
            columns = list(result.keys())
            rows = [list(row) for row in result.fetchall()]

        return {
            "success": True,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows)
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }