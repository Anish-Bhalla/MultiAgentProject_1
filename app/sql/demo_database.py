"""Creates a clearly-labelled synthetic sales database for local demos and tests."""
from __future__ import annotations
import random
import sqlite3
from datetime import date, timedelta
from app.config import get_settings

PRODUCTS = [
    (1, "Trail Backpack", "Outdoor", 79.0),
    (2, "Insulated Bottle", "Accessories", 24.0),
    (3, "Rain Jacket", "Apparel", 119.0),
    (4, "Hiking Shoes", "Footwear", 145.0),
    (5, "Travel Mug", "Accessories", 32.0),
    (6, "Daypack", "Outdoor", 58.0),
    (7, "Thermal Base Layer", "Apparel", 44.0),
    (8, "Camping Lantern", "Equipment", 39.0),
]
CUSTOMERS = [
    (1, "Northwind Outfitters", "North"), (2, "Summit Retail", "West"),
    (3, "Green Path Supply", "South"), (4, "Urban Trek Co", "East"),
    (5, "Blue Ridge Stores", "North"), (6, "Horizon Goods", "West"),
    (7, "Pine & Peak", "South"), (8, "Cedar Retail Group", "East"),
    (9, "Open Trail Market", "Central"), (10, "Evergreen Trading", "Central"),
]


def init_business_db() -> None:
    path = get_settings().business_db
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript("""
          CREATE TABLE IF NOT EXISTS customers (
            customer_id INTEGER PRIMARY KEY, customer_name TEXT NOT NULL, region TEXT NOT NULL
          );
          CREATE TABLE IF NOT EXISTS products (
            product_id INTEGER PRIMARY KEY, product_name TEXT NOT NULL, category TEXT NOT NULL, list_price REAL NOT NULL
          );
          CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, order_date TEXT NOT NULL,
            status TEXT NOT NULL, region TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(customer_id)
          );
          CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL, unit_price REAL NOT NULL, discount_pct REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(order_id), FOREIGN KEY(product_id) REFERENCES products(product_id)
          );
          CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date);
          CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
        """)
        # This demo data is synthetic. Rebuild only when the core tables are empty.
        count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        if count:
            return
        conn.executemany("INSERT INTO customers VALUES (?, ?, ?)", CUSTOMERS)
        conn.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", PRODUCTS)
        rng = random.Random(20261023)
        start = date(2024, 1, 1)
        date_span = (date(2025, 12, 31) - start).days
        statuses = ["completed", "completed", "completed", "returned", "cancelled"]
        order_rows, item_rows = [], []
        item_id = 1
        for order_id in range(1, 241):
            order_day = start + timedelta(days=rng.randint(0, date_span))
            customer_id = rng.randint(1, len(CUSTOMERS))
            region = next(c[2] for c in CUSTOMERS if c[0] == customer_id)
            status = rng.choice(statuses)
            order_rows.append((order_id, customer_id, order_day.isoformat(), status, region))
            for _ in range(rng.randint(1, 4)):
                product = rng.choice(PRODUCTS)
                qty = rng.randint(1, 8)
                discount = rng.choice([0.0, 0.0, 0.05, 0.10, 0.15])
                item_rows.append((item_id, order_id, product[0], qty, product[3], discount))
                item_id += 1
        conn.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", order_rows)
        conn.executemany("INSERT INTO order_items VALUES (?, ?, ?, ?, ?, ?)", item_rows)
        conn.commit()
