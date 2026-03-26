import pandas as pd
import numpy as np
from sqlalchemy import text, inspect
from visualizer import prepare_chart_data


def generate_auto_dashboard(engine) -> dict:
    """
    Auto-generate a dashboard for the connected database.
    Returns KPI cards + chart data for each table.
    """
    try:
        inspector = inspect(engine)
        tables    = inspector.get_table_names()
        dashboard = {
            "kpis":   [],
            "charts": [],
            "tables": []
        }

        for table in tables[:8]:  # max 8 tables
            try:
                result = _analyze_table(engine, table, inspector)
                if result:
                    if result.get("kpis"):
                        dashboard["kpis"].extend(result["kpis"])
                    if result.get("chart"):
                        dashboard["charts"].append(result["chart"])
                    dashboard["tables"].append({
                        "name":      table,
                        "row_count": result.get("row_count", 0),
                        "col_count": result.get("col_count", 0)
                    })
            except Exception:
                pass

        # Limit KPIs to 6
        dashboard["kpis"] = dashboard["kpis"][:6]

        return dashboard

    except Exception as e:
        return {"error": str(e), "kpis": [], "charts": [], "tables": []}


def _analyze_table(engine, table_name: str, inspector) -> dict:
    """Analyze one table and produce chart + KPI data."""

    columns   = inspector.get_columns(table_name)
    col_names = [c["name"] for c in columns]

    # Get row count
    with engine.connect() as conn:
        row_count = conn.execute(
            text(f"SELECT COUNT(*) FROM `{table_name}`")).scalar()

    if row_count == 0:
        return None

    # Classify columns
    date_kws = ["date", "month", "year", "time", "day", "week"]
    num_kws  = ["amount", "total", "count", "price", "revenue",
                "sales", "cost", "value", "qty", "quantity",
                "budget", "profit"]

    date_cols    = []
    numeric_cols = []
    text_cols    = []

    for col in col_names:
        col_lower = col.lower()
        col_type  = str(next(
            (c["type"] for c in columns if c["name"] == col), ""
        )).lower()

        if any(kw in col_lower for kw in date_kws):
            date_cols.append(col)
        elif ("int" in col_type or "float" in col_type or
              "decimal" in col_type or "double" in col_type or
              any(kw in col_lower for kw in num_kws)):
            numeric_cols.append(col)
        elif "varchar" in col_type or "text" in col_type or "char" in col_type:
            text_cols.append(col)

    result = {
        "row_count": row_count,
        "col_count": len(col_names),
        "kpis":      [],
        "chart":     None
    }

    # Generate KPIs
    for num_col in numeric_cols[:2]:
        try:
            with engine.connect() as conn:
                r = conn.execute(text(
                    f"SELECT SUM(`{num_col}`), AVG(`{num_col}`), "
                    f"MAX(`{num_col}`) FROM `{table_name}`"
                )).fetchone()

                if r and r[0] is not None:
                    result["kpis"].append({
                        "label": f"Total {num_col} ({table_name})",
                        "value": _fmt(r[0]),
                        "sub":   f"Avg: {_fmt(r[1])}  Max: {_fmt(r[2])}"
                    })
        except Exception:
            pass

    # Row count KPI
    result["kpis"].append({
        "label": f"{table_name}",
        "value": f"{row_count:,}",
        "sub":   "Total records"
    })

    # Generate chart
    chart = _generate_chart(engine, table_name,
                             date_cols, numeric_cols, text_cols, row_count)
    if chart:
        result["chart"] = chart

    return result


def _generate_chart(engine, table_name,
                    date_cols, numeric_cols, text_cols, row_count) -> dict:
    """Generate the best chart for a table."""

    # Time series chart
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        num_col  = numeric_cols[0]
        try:
            with engine.connect() as conn:
                rows = conn.execute(text(
                    f"SELECT `{date_col}`, SUM(`{num_col}`) as val "
                    f"FROM `{table_name}` "
                    f"GROUP BY `{date_col}` "
                    f"ORDER BY `{date_col}` "
                    f"LIMIT 20"
                )).fetchall()

            if rows:
                cols    = [date_col, f"Total {num_col}"]
                data    = [[str(r[0]), r[1]] for r in rows]
                cd      = prepare_chart_data(cols, data, "line")
                return {
                    "title": f"{num_col} over time ({table_name})",
                    "type":  "line",
                    "data":  cd
                }
        except Exception:
            pass

    # Category aggregation chart
    if text_cols and numeric_cols:
        cat_col = text_cols[0]
        num_col = numeric_cols[0]
        try:
            with engine.connect() as conn:
                rows = conn.execute(text(
                    f"SELECT `{cat_col}`, SUM(`{num_col}`) as val "
                    f"FROM `{table_name}` "
                    f"GROUP BY `{cat_col}` "
                    f"ORDER BY val DESC "
                    f"LIMIT 10"
                )).fetchall()

            if rows:
                cols = [cat_col, f"Total {num_col}"]
                data = [[str(r[0]), r[1]] for r in rows]
                ct   = "pie" if len(rows) <= 6 else "bar"
                cd   = prepare_chart_data(cols, data, ct)
                return {
                    "title": f"{num_col} by {cat_col} ({table_name})",
                    "type":  ct,
                    "data":  cd
                }
        except Exception:
            pass

    # Simple count by category
    if text_cols:
        cat_col = text_cols[0]
        try:
            with engine.connect() as conn:
                rows = conn.execute(text(
                    f"SELECT `{cat_col}`, COUNT(*) as cnt "
                    f"FROM `{table_name}` "
                    f"GROUP BY `{cat_col}` "
                    f"ORDER BY cnt DESC "
                    f"LIMIT 8"
                )).fetchall()

            if rows and len(rows) > 1:
                cols = [cat_col, "Count"]
                data = [[str(r[0]), r[1]] for r in rows]
                ct   = "pie" if len(rows) <= 6 else "bar"
                cd   = prepare_chart_data(cols, data, ct)
                return {
                    "title": f"Distribution of {cat_col} ({table_name})",
                    "type":  ct,
                    "data":  cd
                }
        except Exception:
            pass

    return None


def _fmt(n) -> str:
    if n is None:
        return "—"
    n = float(n)
    if abs(n) >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif abs(n) >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{n:.2f}"