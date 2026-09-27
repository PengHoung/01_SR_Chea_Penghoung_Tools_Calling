import sqlite3

DB_NAME = "shop.db"


def get_connection():
    """Returns a SQLite connection."""
    return sqlite3.connect(DB_NAME)

def init_db():
    """Creates the products table and populates mock inventory."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                stock INTEGER NOT NULL,
                price REAL NOT NULL
            )
            """
        )
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            sample_data = [
                ("Pro Gaming Laptop", "Electronics", 5, 1299.99),
                ("Office Ultrabook Laptop", "Electronics", 0, 899.50),
                ("Wireless Ergonomic Mouse", "Accessories", 15, 49.99),
                ("Mechanical RGB Keyboard", "Accessories", 8, 89.00),
                ("USB-C Fast Charger 65W", "Accessories", 20, 29.99),
                ("Noise-Cancelling Headphones", "Audio", 0, 199.00),
            ]
            cursor.executemany(
                "INSERT INTO products (name, category, stock, price) VALUES (?, ?, ?, ?)",
                sample_data,
            )
            conn.commit()

def query_products_by_keyword(keyword: str = None):
    """Searches products if keyword is provided; otherwise returns all products."""
    with get_connection() as conn:
        cursor = conn.cursor()
        if keyword and keyword.strip():
            cursor.execute(
                "SELECT id, name, category, price FROM products WHERE name LIKE ? OR category LIKE ?",
                (f"%{keyword.strip()}%", f"%{keyword.strip()}%"),
            )
        else:
            cursor.execute("SELECT id, name, category, price FROM products")
        return cursor.fetchall()

def get_all_products():
    """Returns all products in the catalog sorted by price descending."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, category, price FROM products ORDER BY price DESC")
        return cursor.fetchall()

def get_products_by_ids(product_ids: list[int]):
    """Retrieves product details for a list of product IDs."""
    if not product_ids:
        return []
    placeholders = ",".join("?" for _ in product_ids)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT id, name, stock, price FROM products WHERE id IN ({placeholders})",
            product_ids,
        )
        return cursor.fetchall()

def remove_product_by_id(product_id: int) -> bool:
    """Deletes a product from the table by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        return cursor.rowcount > 0

def buy_product_from_db(product_id: int, quantity: int = 1) -> tuple[bool, str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, stock, price FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        if not row:
            return False, f"Product ID {product_id} not found."

        name, stock, price = row
        if stock < quantity:
            return False, f"Not enough stock. Only {stock} remaining."

        new_stock = stock - quantity
        cursor.execute("UPDATE products SET stock = ? WHERE id = ?", (new_stock, product_id))
        conn.commit()

        return True, (
            f"PURCHASE CONFIRMED: 1x '{name}' bought for ${price:.2f}. "
            f"The new updated stock in the database is EXACTLY {new_stock} units."
        )

init_db()