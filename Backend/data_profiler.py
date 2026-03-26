import pandas as pd
import numpy as np
from sqlalchemy import text, inspect


def profile_database(engine) -> dict:
    """
    Run data profiling on all tables in the connected database.
    Returns structured JSON with per-table stats.
    """
    try:
        inspector = inspect(engine)
        tables    = inspector.get_table_names()
        profile   = {}

        for table in tables[:10]:  # max 10 tables
            try:
                profile[table] = _profile_table(engine, table, inspector)
            except Exception as e:
                profile[table] = {"error": str(e)}

        return profile

    except Exception as e:
        return {"error": str(e)}


def _profile_table(engine, table_name: str, inspector) -> dict:
    """Profile a single table."""

    # Get column metadata
    columns    = inspector.get_columns(table_name)
    col_names  = [c["name"] for c in columns]
    col_types  = {c["name"]: str(c["type"]) for c in columns}

    # Get row count
    with engine.connect() as conn:
        count_result = conn.execute(
            text(f"SELECT COUNT(*) FROM `{table_name}`"))
        row_count = count_result.scalar()

    if row_count == 0:
        return {
            "row_count":   0,
            "column_count": len(col_names),
            "columns":     col_types,
            "stats":       {}
        }

    # Sample data for profiling (max 1000 rows)
    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT * FROM `{table_name}` LIMIT 1000"))
        rows   = result.fetchall()
        keys   = list(result.keys())

    df      = pd.DataFrame(rows, columns=keys)
    stats   = {}

    for col in df.columns:
        col_stat = {
            "type":         col_types.get(col, "unknown"),
            "null_count":   int(df[col].isnull().sum()),
            "null_pct":     round(df[col].isnull().sum() / len(df) * 100, 1),
            "unique_count": int(df[col].nunique()),
            "unique_pct":   round(df[col].nunique() / len(df) * 100, 1)
        }

        # Numeric stats
        try:
            numeric = pd.to_numeric(df[col], errors="coerce").dropna()
            if len(numeric) > 0:
                col_stat["min"]  = round(float(numeric.min()), 2)
                col_stat["max"]  = round(float(numeric.max()), 2)
                col_stat["mean"] = round(float(numeric.mean()), 2)
                col_stat["std"]  = round(float(numeric.std()), 2)
                col_stat["is_numeric"] = True
            else:
                col_stat["is_numeric"] = False
        except Exception:
            col_stat["is_numeric"] = False

        # Top values for categorical
        if col_stat["unique_count"] <= 20:
            try:
                top_vals = (
                    df[col].value_counts()
                    .head(5)
                    .to_dict()
                )
                col_stat["top_values"] = {
                    str(k): int(v) for k, v in top_vals.items()
                }
            except Exception:
                pass

        stats[col] = col_stat

    return {
        "row_count":    row_count,
        "column_count": len(col_names),
        "columns":      col_types,
        "stats":        stats
    }