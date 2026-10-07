"""
build_db.py
-----------
Creates a small SQLite database called retail.db with a classic
retail schema: customers, products, orders, order_items.

WHY SQLite: zero setup, no server, the whole database is one file.
Perfect for a portfolio project you want people to clone and run
in 10 seconds. In a real job you'd swap this for Postgres/MySQL,
but the SQL and the app code barely change.

Run this once: python build_db.py
"""

import sqlite3
import random
from datetime import date, timedelta

DB_PATH = "retail.db"
random.seed(42)  # reproducible fake data

# ---------------------------------------------------------------
# 1. Reference data (kept small and readable on purpose)
# ---------------------------------------------------------------
FIRST_NAMES = ["Asha", "Rohan", "Meera", "Vikram", "Priya", "Arjun",
               "Sneha", "Kabir", "Divya", "Rahul", "Ishaan", "Ananya"]
LAST_NAMES = ["Sharma", "Reddy", "Iyer", "Nair", "Rao", "Mehta",
              "Gupta", "Menon", "Kulkarni", "Bose"]
CITIES = ["Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai", "Pune"]

CATEGORIES = ["Electronics", "Home & Kitchen", "Apparel", "Books", "Sports"]
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

# ---------------------------------------------------------------
# 2. Build the database
# ---------------------------------------------------------------
def build():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Wipe any previous run so this script is safely re-runnable
    cur.executescript("""
        DROP TABLE IF EXISTS order_items;
        DROP TABLE IF EXISTS orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS customers;

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

    # --- customers ---
    start = date(2024, 1, 1)
    customers = []
    for i in range(1, 121):  # 120 customers
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        city = random.choice(CITIES)
        signup = start + timedelta(days=random.randint(0, 600))
        customers.append((i, fname, lname, city, signup.isoformat()))
    cur.executemany(
        "INSERT INTO customers VALUES (?,?,?,?,?)", customers
    )

    # --- products ---
    products = [(i + 1, name, cat, price)
                for i, (name, cat, price) in enumerate(PRODUCTS)]
    cur.executemany(
        "INSERT INTO products VALUES (?,?,?,?)", products
    )

    # --- orders + order_items ---
    order_id = 1
    order_item_id = 1
    orders_rows = []
    items_rows = []
    for _ in range(400):  # 400 orders
        cust_id = random.randint(1, 120)
        order_date = start + timedelta(days=random.randint(0, 700))
        orders_rows.append((order_id, cust_id, order_date.isoformat()))

        # each order has 1-4 line items
        for _ in range(random.randint(1, 4)):
            prod_id = random.randint(1, len(PRODUCTS))
            qty = random.randint(1, 3)
            items_rows.append((order_item_id, order_id, prod_id, qty))
            order_item_id += 1

        order_id += 1

    cur.executemany("INSERT INTO orders VALUES (?,?,?)", orders_rows)
    cur.executemany("INSERT INTO order_items VALUES (?,?,?,?)", items_rows)

    conn.commit()
    conn.close()
    print(f"Built {DB_PATH}: {len(customers)} customers, "
          f"{len(products)} products, {len(orders_rows)} orders, "
          f"{len(items_rows)} order items.")


if __name__ == "__main__":
    build()
