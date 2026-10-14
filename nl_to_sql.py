"""
nl_to_sql.py
------------
Core logic: describe the schema, ask Claude for SQL, check it is safe,
and run it. The UI lives in app.py.
"""

import os
import re
import sqlite3

import anthropic
from dotenv import load_dotenv

from build_db import DB_PATH, ensure_db

load_dotenv()

SCHEMA_DESCRIPTION = """
Table: customers
  customer_id INTEGER (primary key)
  first_name TEXT
  last_name TEXT
  city TEXT
  signup_date TEXT (ISO date, e.g. '2024-03-15')

Table: products
  product_id INTEGER (primary key)
  product_name TEXT
  category TEXT (one of: Electronics, Home & Kitchen, Apparel, Books, Sports)
  price REAL (in INR)

Table: orders
  order_id INTEGER (primary key)
  customer_id INTEGER (foreign key -> customers.customer_id)
  order_date TEXT (ISO date)

Table: order_items
  order_item_id INTEGER (primary key)
  order_id INTEGER (foreign key -> orders.order_id)
  product_id INTEGER (foreign key -> products.product_id)
  quantity INTEGER
"""

SYSTEM_PROMPT = """You are a SQL generator for a SQLite database.
Given the schema and a user's question in plain English, output
ONLY a single valid SQLite SELECT query that answers it. No
explanation, no markdown code fences, no semicolon-separated
multiple statements -- just the raw SQL.

Rules:
- Only ever write SELECT statements. Never INSERT, UPDATE, DELETE,
  DROP, ALTER, or anything that modifies data.
- Use table/column names EXACTLY as given in the schema.
- If the question can't be answered with the given schema, output
  exactly: NO_QUERY_POSSIBLE
"""


def generate_sql(question: str, api_key: str | None = None) -> str:
    client = anthropic.Anthropic(
        api_key=api_key or os.environ.get("ANTHROPIC_API_KEY")
    )

    user_message = f"""Database schema:
{SCHEMA_DESCRIPTION}

Question: {question}

Write the SQLite SELECT query."""

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    # The reply can contain a thinking block before the text block,
    # so pick the block whose type is 'text' instead of assuming [0].
    sql = next(
        (block.text for block in response.content if block.type == "text"),
        "",
    ).strip()

    sql = re.sub(r"^```sql\s*|^```\s*|```$", "", sql, flags=re.MULTILINE).strip()
    return sql


FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "ATTACH", "PRAGMA", "VACUUM",
]


def is_safe_select(sql: str) -> tuple[bool, str]:
    cleaned = sql.strip().rstrip(";")

    if not cleaned:
        return False, "Empty query."
    if ";" in cleaned:
        return False, "Multiple statements are not allowed."
    if not cleaned.upper().startswith("SELECT"):
        return False, "Only SELECT statements are allowed."

    upper = cleaned.upper()
    for word in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{word}\b", upper):
            return False, f"Forbidden keyword detected: {word}"

    return True, "OK"


def run_query(sql: str, db_path: str = DB_PATH):
    """Run a SELECT. Only call after is_safe_select() returned True."""
    ensure_db()  # guarantees the tables exist before we connect
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    finally:
        conn.close()
    return columns, rows
