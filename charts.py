"""Charts for the Data Analyst Agent.

Draws a chart from the last query's result table. The default chart type is guessed from the
question ("pie chart", "trend", "scatter"...), and the user can switch type, columns and row
count in the chart panel.
"""
import re

import altair as alt
import pandas as pd
import streamlit as st

KINDS = ["Bar", "Horizontal bar", "Line", "Area", "Pie", "Donut", "Scatter", "Histogram"]
DEFAULT_MAX_POINTS = 30
MAX_SLICES = 10  # pie/donut: keep the biggest 9, group the rest as "Other"
TIME_WORDS = re.compile(r"month|year|date|week|quarter|day", re.I)


def stretch(fn, obj, **kw):
    """Call a Streamlit display function at full width on both old and new Streamlit versions."""
    try:
        return fn(obj, width="stretch", **kw)
    except Exception:  # older Streamlit versions
        return fn(obj, use_container_width=True, **kw)


def guess_kind(hint, x_name=None):
    """Pick a default chart type from the user's question (and the X column name)."""
    h = (hint or "").lower()
    rules = [
        (r"donut|doughnut", "Donut"),
        (r"\bpie\b", "Pie"),
        (r"scatter", "Scatter"),
        (r"histogram|distribution", "Histogram"),
        (r"horizontal", "Horizontal bar"),
        (r"\bbar\b", "Bar"),
        (r"\barea (chart|graph)", "Area"),
        (r"\bline\b|trend|over time|monthly|per month|by month|each month|per year|by year|yearly|daily|weekly", "Line"),
    ]
    for pattern, kind in rules:
        if re.search(pattern, h):
            return kind
    if x_name and TIME_WORDS.search(str(x_name)):
        return "Line"
    return "Bar"


def _pie_data(df_n, x, y):
    data = pd.DataFrame({"label": df_n[x].astype(str).values,
                         "value": pd.to_numeric(df_n[y], errors="coerce").values}).dropna()
    data = data.groupby("label", as_index=False, sort=False)["value"].sum()
    data = data.sort_values("value", ascending=False)
    if len(data) > MAX_SLICES:
        top, rest = data.iloc[:MAX_SLICES - 1], data.iloc[MAX_SLICES - 1:]
        data = pd.concat([top, pd.DataFrame({"label": ["Other"], "value": [rest["value"].sum()]})],
                         ignore_index=True)
    total = data["value"].sum()
    data["pct"] = (data["value"] / total * 100).round(1) if total else 0.0
    data["pct_label"] = data["pct"].map(lambda p: f"{p:.0f}%" if p >= 4 else "")
    return data


def show_chart(df, key, hint=""):
    """Show an interactive chart for df. Does nothing if the result has no numeric column."""
    if df is None or len(df) < 2:
        return
    cols = list(df.columns)
    nums = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    if not nums:
        return
    labels = [c for c in cols if c not in nums] or cols
    x_default = labels[0]
    kind_default = guess_kind(hint, x_default)

    with st.expander("📈 Chart", expanded=True):
        r1 = st.columns(4)
        kind = r1[0].selectbox("Type", KINDS, index=KINDS.index(kind_default), key=f"kind_{key}")
        # pie/donut shares must use every row, otherwise the percentages are wrong
        default_rows = DEFAULT_MAX_POINTS
        if kind in ("Pie", "Donut"):
            default_rows = 5000
        elif kind == "Histogram":
            default_rows = 2000
        n = r1[3].number_input("Max rows", min_value=2, max_value=5000,
                               value=min(len(df), default_rows), key=f"n_{key}_{kind}")
        df_n = df.head(int(n))

        # ---------- Histogram ----------
        if kind == "Histogram":
            y = r1[1].selectbox("Numbers to bin", nums, key=f"hy_{key}")
            data = pd.DataFrame({"value": pd.to_numeric(df_n[y], errors="coerce")}).dropna()
            ch = alt.Chart(data).mark_bar().encode(
                x=alt.X("value:Q", bin=alt.Bin(maxbins=20), title=y),
                y=alt.Y("count()", title="Rows"))
            stretch(st.altair_chart, ch.properties(height=380))
            return

        # ---------- Scatter ----------
        if kind == "Scatter":
            if len(nums) < 2:
                st.info("A scatter chart needs two numeric columns in the result.")
                return
            xs = r1[1].selectbox("X axis (numbers)", nums, key=f"sx_{key}")
            y_opts = [c for c in nums if c != xs]
            ys = r1[2].selectbox("Y axis (numbers)", y_opts, key=f"sy_{key}")
            names = df_n[labels[0]].astype(str).values if labels[0] not in nums else df_n.index.astype(str)
            data = pd.DataFrame({"x": df_n[xs].values, "y": df_n[ys].values, "label": names})
            ch = alt.Chart(data).mark_circle(size=70, opacity=0.7).encode(
                x=alt.X("x:Q", title=xs, scale=alt.Scale(zero=False)),
                y=alt.Y("y:Q", title=ys, scale=alt.Scale(zero=False)),
                tooltip=[alt.Tooltip("label:N", title="row"), alt.Tooltip("x:Q", title=xs),
                         alt.Tooltip("y:Q", title=ys)])
            stretch(st.altair_chart, ch.properties(height=400))
            return

        # ---------- Pie / Donut ----------
        if kind in ("Pie", "Donut"):
            x = r1[1].selectbox("Slice labels", cols, index=cols.index(x_default), key=f"px_{key}")
            y_opts = [c for c in nums if c != x] or nums
            y = r1[2].selectbox("Slice sizes (numbers)", y_opts, key=f"py_{key}")
            data = _pie_data(df_n, x, y)
            if data.empty or (data["value"] < 0).any() or data["value"].sum() <= 0:
                st.warning("A pie chart needs positive numbers. Try a bar chart for this result.")
                return
            tip = [alt.Tooltip("label:N", title=x), alt.Tooltip("value:Q", title=y, format=",.2f"),
                   alt.Tooltip("pct:Q", title="share %")]
            theta = alt.Theta("value:Q", stack=True)
            arcs = alt.Chart(data).mark_arc(outerRadius=140, innerRadius=70 if kind == "Donut" else 0).encode(
                theta=theta, color=alt.Color("label:N", sort=None, title=x), tooltip=tip)
            text = alt.Chart(data).mark_text(radius=162, size=12).encode(
                theta=theta, text=alt.Text("pct_label:N"))
            stretch(st.altair_chart, (arcs + text).properties(height=420))
            if len(df_n) > MAX_SLICES:
                st.caption(f"Showing the {MAX_SLICES - 1} biggest slices; the rest are grouped as 'Other'.")
            return

        # ---------- Bar / Horizontal bar / Line / Area ----------
        x = r1[1].selectbox("X axis (labels)", cols, index=cols.index(x_default), key=f"x_{key}")
        y_opts = [c for c in nums if c != x] or nums
        y = r1[2].selectbox("Y axis (numbers)", y_opts, key=f"y_{key}")
        g_opts = ["(none)"] + [c for c in cols if c not in (x, y)]
        g_default = 0
        if len(labels) >= 2 and labels[1] in g_opts and x == labels[0]:
            g_default = g_opts.index(labels[1])  # e.g. month, status, orders -> one series per status
        group = st.selectbox("Split into series by (optional)", g_opts, index=g_default,
                             key=f"g_{key}")

        data = pd.DataFrame({"label": df_n[x].astype(str).values, "value": df_n[y].values})
        tip = [alt.Tooltip("label:O", title=x), alt.Tooltip("value:Q", title=y)]
        color = alt.Undefined
        if group != "(none)":
            data["group"] = df_n[group].astype(str).values
            tip.append(alt.Tooltip("group:N", title=group))
            color = alt.Color("group:N", title=group)

        x_cat = alt.X("label:O", sort=None, title=x, axis=alt.Axis(labelAngle=-45))
        y_val = alt.Y("value:Q", title=y)
        base = alt.Chart(data)
        if kind == "Bar":
            ch = base.mark_bar().encode(x=x_cat, y=y_val, color=color, tooltip=tip)
        elif kind == "Horizontal bar":
            ch = base.mark_bar().encode(y=alt.Y("label:O", sort=None, title=x),
                                        x=alt.X("value:Q", title=y), color=color, tooltip=tip)
        elif kind == "Line":
            ch = base.mark_line(point=True).encode(x=x_cat, y=y_val, color=color, tooltip=tip)
        else:
            ch = base.mark_area(opacity=0.5, line=True).encode(x=x_cat, y=y_val, color=color, tooltip=tip)
        stretch(st.altair_chart, ch.properties(height=380))
