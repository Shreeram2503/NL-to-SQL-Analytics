"""
build_db.py
-----------
Builds the SQLite retail database and guarantees it exists before any query.

Safety features (added after a 'no such table' bug on the hosted app):
  - The database is built in a temporary file and then swapped into place
    in one step (os.replace), so nobody ever sees a half-built database.
  - ensure_db() checks that the real tables exist, not just the file.
  - A lock stops two visitors from building at the same time.
"""

import os
import random
import sqlite3
import tempfile
import threading
from datetime import date, timedelta

# Temp folder: always writable, even on read-only hosts.
DB_PATH = os.path.join(tempfile.gettempdir(), "retail.db")
REQUIRED_TABLES = {"customers", "products", "orders", "order_items"}

_build_lock = threading.Lock()

FIRST_NAMES = ["Asha", "Rohan", "Meera", "Vikram", "Priya", "Arjun",
               "Sneha", "Kabir", "Divya", "Rahul", "Ishaan", "Ananya"]
LAST_NAMES = ["Sharma", "Reddy", "Iyer", "Nair", "Rao", "Mehta",
              "Gupta", "Menon", "Kulkarni", "Bose"]
CITIES = ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune"]

PRODUCTS = [
    ("Wireless Mouse", "Electronics", 799),
    ("Mechanical Keyboard", "Electronics", 3499),
    ("USB-C Hub", "Electronics", 1299),
    ("Noise Cancelling Headphones", "Electronics", 5999),
    ("Non-stick Pan", "Home & Kitchen", 899),
    ("Electric Kettle", "Home & Kitchen", 1199),
    ("Cotton Bedsheet Set", "Home & Kitchen", 1499),
    ("Running Shoes", "Sports", 2999),
    ("Yoga Mat", "Sports", 699),
    ("Cricket Bat", "Sports", 1899),
    ("Men's T-Shirt", "Apparel", 499),
    ("Women's Jacket", "Apparel", 2299),
    ("Data Engineering Handbook", "Books", 899),
    ("Python Crash Course", "Books", 799),
    ("Desk Lamp", "Home & Kitchen", 999),
]


def build(target=None):
    """Build the database in a temp file, then swap it into place."""
    target = target or DB_PATH
    tmp_path = f"{target}.{os.getpid()}.building"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)

    rng = random.Random(42)  # same fake data every time
    conn = sqlite3.connect(tmp_path)
    try:
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE customers (
                customer_id INTEGER PRIMARY KEY,
                first_name  TEXT NOT NULL,
                last_name   TEXT NOT NULL,
                city        TEXT NOT NULL,
                signup_date TEXT NOT NULL
            );
            CREATE TABLE products (
                product_id INTEGER PRIMARY KEY,
                product_name TEXT NOT NULL,
                category     TEXT NOT NULL,
                price        REAL NOT NULL
            );
            CREATE TABLE orders (
                order_id    INTEGER PRIMARY KEY,
                customer_id INTEGER NOT NULL,
                order_date  TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
            );
            CREATE TABLE order_items (
                order_item_id INTEGER PRIMARY KEY,
                order_id      INTEGER NOT NULL,
                product_id    INTEGER NOT NULL,
                quantity      INTEGER NOT NULL,
                FOREIGN KEY (order_id)   REFERENCES orders(order_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
        """)

        start = date(2024, 1, 1)
        customers = []
        for i in range(1, 121):
            customers.append((
                i, rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES),
                rng.choice(CITIES),
                (start + timedelta(days=rng.randint(0, 600))).isoformat(),
            ))
        cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)

        products = [(i + 1, n, c, p) for i, (n, c, p) in enumerate(PRODUCTS)]
        cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products)

        orders_rows, items_rows = [], []
        order_item_id = 1
        for order_id in range(1, 401):
            cust_id = rng.randint(1, 120)
            order_date = start + timedelta(days=rng.randint(0, 700))
            orders_rows.append((order_id, cust_id, order_date.isoformat()))
            for _ in range(rng.randint(1, 4)):
                items_rows.append((order_item_id, order_id,
                                   rng.randint(1, len(PRODUCTS)),
                                   rng.randint(1, 3)))
                order_item_id += 1
        cur.executemany("INSERT INTO orders VALUES (?,?,?)", orders_rows)
        cur.executemany("INSERT INTO order_items VALUES (?,?,?,?)", items_rows)
        conn.commit()
    finally:
        conn.close()

    os.replace(tmp_path, target)  # one-step swap: never half-built
    print(f"Built {target}: {len(customers)} customers, {len(products)} "
          f"products, {len(orders_rows)} orders, {len(items_rows)} order items.")


def db_ready(path=None):
    """True only if the file exists AND all four tables are inside it."""
    path = path or DB_PATH
    if not os.path.exists(path):
        return False
    try:
        conn = sqlite3.connect(path)
        try:
            names = {row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
        return REQUIRED_TABLES <= names
    except sqlite3.Error:
        return False


def ensure_db():
    """Call before any query. Builds the database if it is missing or empty."""
    if db_ready():
        return
    with _build_lock:
        if not db_ready():  # re-check: another visitor may have just built it
            build()


if __name__ == "__main__":
    build()
