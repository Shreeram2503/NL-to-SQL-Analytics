"""
nl_to_sql.py
------------
The core logic, separated from the Streamlit UI on purpose.

WHY separate this file from app.py: it's a portfolio best practice.
Recruiters and interviewers who open your repo should see that you
separate "business logic" from "UI code". It also means you could
swap Streamlit for a Flask API later without touching this file.

Three responsibilities live here:
  1. Describe the database schema to the LLM (so it knows what
     tables/columns exist).
  2. Ask the LLM to turn a plain-English question into SQL.
  3. Check the SQL is SAFE before anything executes it.
"""

import os
import sqlite3
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()

from build_db import DB_PATH
DB_PATH = "retail.db"

# -----------------------------------------------------------------
# 1. Schema description
# -----------------------------------------------------------------
# WHY hardcode this instead of querying it live: for a small fixed
# schema, a hand-written description is clearer and cheaper (fewer
# tokens) than dumping raw PRAGMA output. For a bigger project you'd
# generate this from the database automatically -- see
# `describe_schema_from_db()` below for how.

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


def describe_schema_from_db(db_path: str = DB_PATH) -> str:
    """
    Optional alternative to the hardcoded SCHEMA_DESCRIPTION above.
    Reads the *actual* table/column names straight from SQLite.
    Useful if your schema changes and you don't want to update the
    docstring by hand. Not used by default, but wired up so you can
    swap it in inside generate_sql() if you want.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]

    lines = []
    for table in tables:
        cur.execute(f"PRAGMA table_info({table})")
        cols = cur.fetchall()
        col_desc = ", ".join(f"{c[1]} {c[2]}" for c in cols)
        lines.append(f"Table: {table}\n  {col_desc}")
    conn.close()
    return "\n\n".join(lines)


# -----------------------------------------------------------------
# 2. Ask Claude to write the SQL
# -----------------------------------------------------------------
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
    """
    Sends the schema + question to Claude and returns the raw SQL
    string it responds with (no execution yet -- that's a separate,
    deliberately careful step below).
    """
    client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

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

    sql = next((block.text for block in response.content if block.type == "text"),"").strip()

    # Claude sometimes wraps SQL in ```sql fences despite instructions.
    # Strip them defensively rather than trusting the prompt alone.
    sql = re.sub(r"^```sql\s*|^```\s*|```$", "", sql, flags=re.MULTILINE).strip()

    return sql


# -----------------------------------------------------------------
# 3. Safety check -- THE MOST IMPORTANT FUNCTION IN THIS PROJECT
# -----------------------------------------------------------------
# WHY this exists: an LLM is not a trusted component. Prompt
# injection, a bad model response, or a bug could produce SQL that
# deletes data. NEVER execute LLM-generated SQL against a real
# database without a check like this. This is exactly the kind of
# thing an interviewer will ask you about -- be ready to explain it.

FORBIDDEN_KEYWORDS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE",
    "TRUNCATE", "REPLACE", "ATTACH", "PRAGMA", "VACUUM",
]


def is_safe_select(sql: str) -> tuple[bool, str]:
    """
    Returns (is_safe, reason). Only allows a single SELECT statement.
    """
    cleaned = sql.strip().rstrip(";")

    if not cleaned:
        return False, "Empty query."

    if ";" in cleaned:
        return False, "Multiple statements are not allowed."

    if not cleaned.upper().startswith("SELECT"):
        return False, "Only SELECT statements are allowed."

    upper = cleaned.upper()
    for word in FORBIDDEN_KEYWORDS:
        # \b so we don't false-positive on e.g. a column named 'created_at'
        if re.search(rf"\b{word}\b", upper):
            return False, f"Forbidden keyword detected: {word}"

    return True, "OK"


def run_query(sql: str, db_path: str = DB_PATH):
    """
    Executes a SELECT query and returns (columns, rows).
    Only call this AFTER is_safe_select() has returned True --
    this function does not re-check safety itself, by design, so
    the safety check is never accidentally skipped by a caller
    that forgets to call it.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute(sql)
    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()
    conn.close()
    return columns, rows
