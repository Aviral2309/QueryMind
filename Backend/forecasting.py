import pandas as pd
import numpy as np


def forecast_series(columns: list, rows: list,
                    periods: int = 3) -> dict:
    """
    Simple forecasting using linear regression.
    Input: query result columns + rows
    Output: forecast dict with predicted values
    """
    if not columns or not rows or len(rows) < 4:
        return {}

    try:
        df = pd.DataFrame(rows, columns=columns)

        # Find date col and numeric col
        date_kws = ["date", "month", "year", "time", "day"]
        date_col = None
        num_col  = None

        for col in columns:
            if any(kw in col.lower() for kw in date_kws):
                date_col = col
                break

        for col in columns:
            if col == date_col:
                continue
            try:
                pd.to_numeric(df[col], errors="raise")
                num_col = col
                break
            except Exception:
                pass

        if not date_col or not num_col:
            return {}

        df[num_col] = pd.to_numeric(df[num_col], errors="coerce")
        df = df.dropna(subset=[num_col])

        if len(df) < 4:
            return {}

        # Use index as x-axis for regression
        x = np.arange(len(df)).reshape(-1, 1)
        y = df[num_col].values

        # Simple linear regression (numpy)
        x_flat  = x.flatten()
        slope   = np.polyfit(x_flat, y, 1)[0]
        intercept = np.polyfit(x_flat, y, 1)[1]

        # Generate forecast
        forecast_x     = np.arange(len(df), len(df) + periods)
        forecast_vals  = slope * forecast_x + intercept

        # Get last few date labels for context
        last_labels = df[date_col].astype(str).tolist()[-3:]

        return {
            "available":       True,
            "date_column":     date_col,
            "value_column":    num_col,
            "historical_count": len(df),
            "trend":           "upward" if slope > 0 else "downward",
            "slope":           round(float(slope), 4),
            "forecast":        [round(float(v), 2) for v in forecast_vals],
            "forecast_label":  f"Next {periods} periods",
            "last_labels":     last_labels,
            "message": (
                f"{num_col} shows a "
                f"{'positive' if slope > 0 else 'negative'} trend. "
                f"Forecast for next {periods} periods: "
                + ", ".join(f"{v:,.2f}" for v in forecast_vals)
            )
        }

    except Exception:
        return {}