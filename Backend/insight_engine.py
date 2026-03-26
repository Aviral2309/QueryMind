import pandas as pd
import numpy as np
from scipy import stats


def generate_insights(df: pd.DataFrame, question: str = "") -> dict:
    """
    Main entry point. Returns insights + anomalies.
    """
    if df is None or df.empty:
        return {"insights": [], "anomalies": []}

    insights  = []
    anomalies = []

    insights  += _summary_stats(df)
    insights  += _top_contributors(df)
    insights  += _growth_detection(df)
    anomalies += _detect_anomalies(df)

    return {
        "insights":  insights[:6],   # max 6 insights
        "anomalies": anomalies[:4]   # max 4 anomaly alerts
    }


def _get_numeric_cols(df):
    return df.select_dtypes(include=[np.number]).columns.tolist()


def _get_text_cols(df):
    return df.select_dtypes(include=["object"]).columns.tolist()


def _get_date_cols(df):
    date_kws = ["date", "month", "year", "time", "day", "week", "period"]
    return [
        c for c in df.columns
        if any(kw in str(c).lower() for kw in date_kws)
    ]


def _summary_stats(df) -> list:
    insights = []
    numeric  = _get_numeric_cols(df)

    for col in numeric[:2]:  # max 2 columns
        series = df[col].dropna()
        if len(series) == 0:
            continue

        total  = series.sum()
        mean   = series.mean()
        mx     = series.max()
        mn     = series.min()

        # Format numbers nicely
        def fmt(n):
            if abs(n) >= 1_000_000:
                return f"{n/1_000_000:.1f}M"
            elif abs(n) >= 1_000:
                return f"{n/1_000:.1f}K"
            return f"{n:.2f}"

        insights.append(
            f"{col}: total {fmt(total)}, "
            f"avg {fmt(mean)}, "
            f"range {fmt(mn)} – {fmt(mx)}"
        )

    return insights


def _top_contributors(df) -> list:
    insights = []
    text_cols    = _get_text_cols(df)
    numeric_cols = _get_numeric_cols(df)

    if not text_cols or not numeric_cols:
        return insights

    cat_col = text_cols[0]
    num_col = numeric_cols[0]

    try:
        grouped = (
            df.groupby(cat_col)[num_col]
            .sum()
            .sort_values(ascending=False)
        )

        if len(grouped) == 0:
            return insights

        top_name  = grouped.index[0]
        top_val   = grouped.iloc[0]
        total_val = grouped.sum()

        if total_val > 0:
            pct = (top_val / total_val) * 100
            insights.append(
                f"Top contributor: {top_name} accounts for "
                f"{pct:.1f}% of total {num_col}"
            )

        if len(grouped) >= 2:
            bottom_name = grouped.index[-1]
            bottom_val  = grouped.iloc[-1]
            insights.append(
                f"Lowest: {bottom_name} with "
                f"{bottom_val:,.2f} {num_col}"
            )

    except Exception:
        pass

    return insights


def _growth_detection(df) -> list:
    insights  = []
    date_cols = _get_date_cols(df)
    num_cols  = _get_numeric_cols(df)

    if not date_cols or not num_cols:
        return insights

    date_col = date_cols[0]
    num_col  = num_cols[0]

    try:
        temp = df[[date_col, num_col]].dropna().copy()
        temp = temp.sort_values(date_col)

        if len(temp) < 2:
            return insights

        first_val = temp[num_col].iloc[0]
        last_val  = temp[num_col].iloc[-1]

        if first_val != 0:
            change_pct = ((last_val - first_val) / abs(first_val)) * 100
            direction  = "increased" if change_pct > 0 else "decreased"
            insights.append(
                f"{num_col} {direction} by "
                f"{abs(change_pct):.1f}% "
                f"from start to end of period"
            )

        # Peak detection
        peak_idx  = temp[num_col].idxmax()
        peak_date = temp.loc[peak_idx, date_col]
        peak_val  = temp.loc[peak_idx, num_col]
        insights.append(
            f"Peak {num_col}: {peak_val:,.2f} at {peak_date}"
        )

    except Exception:
        pass

    return insights


def _detect_anomalies(df) -> list:
    anomalies = []
    num_cols  = _get_numeric_cols(df)

    for col in num_cols[:2]:
        series = df[col].dropna()
        if len(series) < 4:
            continue

        try:
            z_scores = np.abs(stats.zscore(series))
            outlier_indices = np.where(z_scores > 2.5)[0]

            for idx in outlier_indices[:2]:  # max 2 per column
                val = series.iloc[idx]
                anomalies.append({
                    "column":  col,
                    "value":   round(float(val), 2),
                    "message": (
                        f"Unusual value detected in {col}: "
                        f"{val:,.2f} is significantly "
                        f"{'higher' if val > series.mean() else 'lower'} "
                        f"than the average ({series.mean():,.2f})"
                    ),
                    "severity": "high" if abs(
                        stats.zscore([val],
                        ddof=0)[0]) > 3.5 else "medium"
                })
        except Exception:
            pass

    return anomalies


def rows_to_dataframe(columns: list, rows: list) -> pd.DataFrame:
    """Convert query result to pandas DataFrame."""
    if not columns or not rows:
        return pd.DataFrame()
    try:
        df = pd.DataFrame(rows, columns=columns)
        # Try to convert numeric strings
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except (ValueError, TypeError):
                pass
        return df
    except Exception:
        return pd.DataFrame()