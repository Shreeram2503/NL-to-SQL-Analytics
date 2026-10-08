"""
app.py
------
The Streamlit UI. Deliberately thin -- almost everything interesting
happens in nl_to_sql.py. This file's only job is: take input, call
the logic functions in the right order, display output.

Run locally with:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
from nl_to_sql import generate_sql, is_safe_select, run_query
import os
from build_db import build, DB_PATH

if not os.path.exists(DB_PATH):
    build()

st.set_page_config(page_title="NL to SQL Analytics", page_icon="📊")

st.title("Ask your database a question")
st.caption(
    "Type a question in plain English. Claude converts it to SQL, "
    "the query runs against a retail database, and you get a table "
    "and chart back -- no SQL knowledge required."
)

with st.expander("Example questions to try"):
    st.markdown(
        "- What are the top 5 products by total quantity sold?\n"
        "- Which city has the most customers?\n"
        "- What is the total revenue by product category?\n"
        "- Show me the 10 most recent orders\n"
        "- Which customers signed up in 2024 but have never ordered?"
    )

question = st.text_input("Your question", placeholder="e.g. What are the top 5 products by revenue?")

if st.button("Ask", type="primary") and question:
    with st.spinner("Thinking..."):
        try:
            sql = generate_sql(question)
        except Exception as e:
            st.error(f"Couldn't reach the AI model: {e}")
            st.stop()

    if sql.strip() == "NO_QUERY_POSSIBLE":
        st.warning("That question can't be answered from this database's schema.")
        st.stop()

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    # --- THE SAFETY GATE ---
    # This is non-negotiable: we never run SQL from an LLM without
    # checking it first. See nl_to_sql.is_safe_select for the logic.
    safe, reason = is_safe_select(sql)
    if not safe:
        st.error(f"Blocked for safety: {reason}")
        st.stop()

    try:
        columns, rows = run_query(sql)
    except Exception as e:
        st.error(f"The database rejected this query: {e}")
        st.stop()

    if not rows:
        st.info("Query ran successfully but returned no rows.")
        st.stop()

    df = pd.DataFrame(rows, columns=columns)

    st.subheader("Results")
    st.dataframe(df, use_container_width=True)

    # --- Auto-chart: only if it makes sense ---
    # Heuristic: one text/categorical column + one numeric column
    # is the classic "bar chart" shape. Anything else, we just show
    # the table -- forcing a chart onto data that doesn't fit one
    # (like a single row, or 5 numeric columns) does more harm than
    # good.
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    non_numeric_cols = [c for c in df.columns if c not in numeric_cols]

    if len(numeric_cols) >= 1 and len(non_numeric_cols) == 1 and len(df) <= 25:
        st.subheader("Chart")
        chart_df = df.set_index(non_numeric_cols[0])[numeric_cols[0]]
        st.bar_chart(chart_df)
