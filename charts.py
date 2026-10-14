"""
charts.py
---------
Decides whether a query result can be drawn as a chart, and how.
Kept separate from app.py so it can be tested without Streamlit.
"""

import pandas as pd

TIME_HINTS = ("date", "month", "year", "week", "day")
MAX_ROWS = 50


def _is_id(name) -> bool:
    n = str(name).lower()
    return n == "id" or n.endswith("_id")


def _is_time(name) -> bool:
    n = str(name).lower()
    return any(h in n for h in TIME_HINTS)


def pick_chart(df: pd.DataFrame):
    """
    Returns (kind, chart_df, note).
      kind: 'bar', 'line' or None
      chart_df: a DataFrame indexed by label, with 1-3 numeric columns
      note: the reason, when kind is None
    """
    if len(df) < 2:
        return None, None, "the result has only one row, so the table is clearer."
    if len(df) > MAX_ROWS:
        return None, None, f"the result has more than {MAX_ROWS} rows."

    is_num = lambda c: (pd.api.types.is_numeric_dtype(df[c])
                        and not pd.api.types.is_bool_dtype(df[c]))
    numeric = [c for c in df.columns if is_num(c)]

    # Measures = real numbers to plot (at most 3). ID columns are labels, not measures.
    non_id_numeric = [c for c in numeric if not _is_id(c)]
    measures = non_id_numeric[:3]

    # Labels = everything that is not a plotted number or an extra number.
    labels = [c for c in df.columns if c not in non_id_numeric]

    if not measures:
        return None, None, "there is no numeric column to plot."
    if not labels:
        return None, None, "there is no label column (like a name or date)."

    # One time-like label -> line chart, sorted by time.
    if len(labels) == 1 and _is_time(labels[0]):
        out = df[[labels[0]] + measures].copy()
        out[labels[0]] = out[labels[0]].astype(str)
        out = out.sort_values(labels[0]).set_index(labels[0])
        return "line", out, ""

    # Otherwise bar chart. Several label columns are joined into one label.
    label_cols = labels[:3]
    names = df[label_cols[0]].astype(str)
    for c in label_cols[1:]:
        names = names + " - " + df[c].astype(str)

    # Duplicate labels would break the chart, so number them.
    if names.duplicated().any():
        names = names + " #" + (names.groupby(names).cumcount() + 1).astype(str)

    out = df[measures].copy()
    out.index = names
    return "bar", out, ""
