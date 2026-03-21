from db_connector import get_db
from sqlalchemy import text


def execute_query(sql: str) -> dict:
    try:
        db = get_db()
        with db._engine.connect() as conn:
            result  = conn.execute(text(sql))
            columns = list(result.keys())
            rows    = [list(row) for row in result.fetchall()]
        return {
            "success":   True,
            "columns":   columns,
            "rows":      rows,
            "row_count": len(rows)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}