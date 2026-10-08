# Ask Your Database — Natural Language to SQL Analytics Assistant

Type a question in plain English ("what are the top 5 products by revenue?")
and get back a real SQL query, a results table, and an auto-generated chart —
no SQL knowledge required to use it.

**\[Live demo link — https://nl-2-sql-assistant.streamlit.app/]**

## Why this project

Most entry-level data portfolios show static dashboards or one-off EDA
notebooks. This is a small working *application*: it takes live user input,
calls an LLM to generate SQL, validates that SQL is safe, executes it
against a real database, and renders the result — end to end, deployed,
clickable.

## Architecture

```
User question (Streamlit)
        |
        v
Claude API (schema + question -> SQL)
        |
        v
Safety check (SELECT-only, single statement)
        |
        v
SQLite database (executes the query)
        |
        v
Results table (pandas) -> auto chart (if the shape fits)
```

## Tech stack

* **Python** — core language
* **Streamlit** — web UI, no frontend code needed
* **Anthropic Claude API** — natural language to SQL translation
* **SQLite** — lightweight embedded database (retail dataset, generated
synthetically — see `build\_db.py`)
* **Pandas** — results handling and chart data shaping

## Database schema

Four tables: `customers`, `products`, `orders`, `order\_items` — a standard
normalized retail schema. See `nl\_to\_sql.py` for the full column list.

## Setup

```bash
# 1. Clone and enter the project
git clone <your-repo-url>
cd nl2sql\_project

# 2. Install dependencies
pip install -r requirements.txt

# 3. Build the database (creates retail.db)
python build\_db.py

# 4. Add your API key
cp .env.example .env
# then edit .env and paste your key from https://console.anthropic.com

# 5. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501`.

## Safety design

LLM output is never trusted blindly. Every generated query passes through
`is\_safe\_select()` before it touches the database:

* Must start with `SELECT`
* Must be a single statement (no `;`-chained commands)
* Blocks `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, and other
data-modifying keywords, even if they appear inside a otherwise
SELECT-shaped query

This is the part of the project worth explaining in an interview — it shows
you think about LLMs as an untrusted input source, not a black box you
blindly execute output from.

## Deploying (free)

1. Push this repo to GitHub (make sure `.env` is *not* included — check
`.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io), connect your
GitHub repo
3. In the app's "Secrets" settings, add:

```
   ANTHROPIC\_API\_KEY = "your-key-here"
   ```

4. Deploy — you'll get a public URL to put on your resume and LinkedIn

## Possible extensions

* Add query result caching so repeated questions don't re-call the API
* Support more chart types (line charts for time-series questions)
* Add a query history sidebar
* Swap SQLite for Postgres to demonstrate a "real" production database

