"""
app.py
------
The Streamlit UI. Run locally with:  streamlit run app.py
"""

import pandas as pd
import streamlit as st

from charts import pick_chart
from nl_to_sql import generate_sql, is_safe_select, run_query

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

question = st.text_input(
    "Your question",
    placeholder="e.g. What are the top 5 products by revenue?",
)

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

    # Safety gate: never run model-written SQL without checking it.
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

    kind, chart_df, note = pick_chart(df)
    if kind == "bar":
        st.subheader("Chart")
        st.bar_chart(chart_df)
    elif kind == "line":
        st.subheader("Chart")
        st.line_chart(chart_df)
    else:
        st.caption(f"No chart for this result: {note}")
