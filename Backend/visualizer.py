def detect_chart_type(columns: list, rows: list) -> str:
    """
    Rule-based chart type detection based on result shape.
    Returns: 'bar', 'line', 'pie', or 'none'
    """
    if not rows or not columns:
        return "none"

    num_cols = len(columns)
    num_rows = len(rows)

    if num_rows == 0:
        return "none"

    # Count numeric vs text columns
    numeric_cols = []
    text_cols    = []

    for i, col in enumerate(columns):
        sample_vals = [row[i] for row in rows[:5] if row[i] is not None]
        is_numeric  = False
        for v in sample_vals:
            try:
                float(str(v).replace(",", ""))
                is_numeric = True
                break
            except:
                pass
        if is_numeric:
            numeric_cols.append(i)
        else:
            text_cols.append(i)

    # Detect date/time column
    date_keywords = ["date", "month", "year", "time", "day", "week", "period"]
    has_date_col  = any(
        any(kw in str(col).lower() for kw in date_keywords)
        for col in columns
    )

    # Decision logic
    if num_cols == 2:
        if has_date_col and len(numeric_cols) >= 1:
            return "line"          # time series
        if len(text_cols) >= 1 and len(numeric_cols) >= 1:
            if num_rows <= 6:
                return "pie"       # small categorical → pie
            return "bar"           # larger categorical → bar

    if num_cols >= 2 and len(numeric_cols) >= 1 and len(text_cols) >= 1:
        if has_date_col:
            return "line"
        return "bar"

    return "none"


def prepare_chart_data(columns: list, rows: list, chart_type: str) -> dict:
    """
    Prepare data in Chart.js format.
    """
    if chart_type == "none" or not rows:
        return {}

    # Find label column (first text col) and value column (first numeric col)
    label_col = 0
    value_col = 1 if len(columns) > 1 else 0

    labels = [str(row[label_col]) for row in rows]
    values = []
    for row in rows:
        try:
            values.append(float(str(row[value_col]).replace(",", "")))
        except:
            values.append(0)

    colors = [
        "rgba(0,229,255,0.8)",    "rgba(123,97,255,0.8)",
        "rgba(0,214,143,0.8)",    "rgba(255,181,71,0.8)",
        "rgba(255,77,106,0.8)",   "rgba(99,179,237,0.8)",
        "rgba(246,173,85,0.8)",   "rgba(154,230,180,0.8)",
    ]

    chart_colors = [colors[i % len(colors)] for i in range(len(labels))]

    if chart_type == "pie":
        return {
            "type": "pie",
            "data": {
                "labels": labels,
                "datasets": [{
                    "data":             values,
                    "backgroundColor":  chart_colors,
                    "borderColor":      "rgba(255,255,255,0.1)",
                    "borderWidth":      1
                }]
            },
            "options": {
                "responsive":          True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {
                        "position": "right",
                        "labels":   {"color": "#c8d0e8", "font": {"size": 11}}
                    }
                }
            }
        }

    border_colors = [c.replace("0.8", "1") for c in chart_colors]

    return {
        "type": chart_type,
        "data": {
            "labels": labels,
            "datasets": [{
                "label":           columns[value_col],
                "data":            values,
                "backgroundColor": chart_colors,
                "borderColor":     border_colors,
                "borderWidth":     2,
                "tension":         0.4,
                "fill":            chart_type == "line",
                "pointRadius":     4 if chart_type == "line" else 0
            }]
        },
        "options": {
            "responsive":          True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": False}
            },
            "scales": {
                "x": {
                    "ticks": {"color": "#7a8aaa", "font": {"size": 11}},
                    "grid":  {"color": "rgba(255,255,255,0.04)"}
                },
                "y": {
                    "ticks": {"color": "#7a8aaa", "font": {"size": 11}},
                    "grid":  {"color": "rgba(255,255,255,0.06)"}
                }
            }
        }
    }