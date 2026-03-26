def detect_chart_type(columns: list, rows: list) -> str:
    if not rows or not columns:
        return "none"

    num_cols  = len(columns)
    num_rows  = len(rows)

    numeric_cols = []
    text_cols    = []

    for i, col in enumerate(columns):
        sample = [row[i] for row in rows[:5] if row[i] is not None]
        is_num = False
        for v in sample:
            try:
                float(str(v).replace(",", ""))
                is_num = True
                break
            except:
                pass
        if is_num:
            numeric_cols.append(i)
        else:
            text_cols.append(i)

    date_kws     = ["date", "month", "year", "time", "day", "week", "period"]
    has_date_col = any(
        any(kw in str(col).lower() for kw in date_kws)
        for col in columns
    )

    if num_cols == 1 and len(numeric_cols) == 1:
        return "none"

    if num_cols == 2:
        if has_date_col and len(numeric_cols) >= 1:
            return "line"
        if len(text_cols) >= 1 and len(numeric_cols) >= 1:
            return "pie" if num_rows <= 6 else "bar"

    if num_cols >= 2 and len(numeric_cols) >= 1 and len(text_cols) >= 1:
        if has_date_col:
            return "line"
        return "bar"

    if num_cols >= 3 and len(numeric_cols) >= 2:
        return "bar"

    return "none"


def prepare_chart_data(columns: list, rows: list, chart_type: str) -> dict:
    if chart_type == "none" or not rows:
        return {}

    label_col = 0
    value_col = 1 if len(columns) > 1 else 0

    labels = [str(row[label_col]) for row in rows]
    values = []
    for row in rows:
        try:
            values.append(float(str(row[value_col]).replace(",", "")))
        except:
            values.append(0)

    # Red/Black theme colors
    colors = [
        "rgba(220,38,38,0.85)",   "rgba(185,28,28,0.85)",
        "rgba(239,68,68,0.85)",   "rgba(127,29,29,0.85)",
        "rgba(252,165,165,0.85)", "rgba(254,202,202,0.85)",
        "rgba(153,27,27,0.85)",   "rgba(248,113,113,0.85)",
    ]
    chart_colors  = [colors[i % len(colors)] for i in range(len(labels))]
    border_colors = ["rgba(220,38,38,1)" for _ in labels]

    grid_color  = "rgba(255,255,255,0.05)"
    tick_color  = "#6b7280"
    legend_color = "#9ca3af"

    if chart_type == "pie":
        return {
            "type": "pie",
            "data": {
                "labels":   labels,
                "datasets": [{
                    "data":            values,
                    "backgroundColor": chart_colors,
                    "borderColor":     "rgba(0,0,0,0.3)",
                    "borderWidth":     2
                }]
            },
            "options": {
                "responsive":          True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {
                        "position": "right",
                        "labels":   {
                            "color":    legend_color,
                            "font":     {"size": 11},
                            "padding":  16
                        }
                    }
                }
            }
        }

    return {
        "type": chart_type,
        "data": {
            "labels":   labels,
            "datasets": [{
                "label":           columns[value_col] if len(columns) > 1 else "Value",
                "data":            values,
                "backgroundColor": chart_colors,
                "borderColor":     border_colors,
                "borderWidth":     2,
                "tension":         0.4,
                "fill":            chart_type == "line",
                "pointRadius":     4 if chart_type == "line" else 0,
                "pointBackgroundColor": "rgba(220,38,38,1)"
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
                    "ticks": {"color": tick_color, "font": {"size": 11}},
                    "grid":  {"color": grid_color}
                },
                "y": {
                    "ticks": {"color": tick_color, "font": {"size": 11}},
                    "grid":  {"color": grid_color}
                }
            }
        }
    }


def get_data_summary(columns: list, rows: list) -> dict:
    """Generate statistical summary for numeric columns."""
    if not rows or not columns:
        return {}

    summary = {}
    for i, col in enumerate(columns):
        vals = []
        for row in rows:
            try:
                vals.append(float(str(row[i]).replace(",", "")))
            except:
                pass

        if vals:
            summary[col] = {
                "min":   round(min(vals), 2),
                "max":   round(max(vals), 2),
                "avg":   round(sum(vals) / len(vals), 2),
                "sum":   round(sum(vals), 2),
                "count": len(vals)
            }

    return summary