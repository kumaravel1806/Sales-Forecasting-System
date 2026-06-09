import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

DB_PATH = None


def _parse_db_url(url: str) -> str:
    # Expect sqlite:///backend/data/app.db
    if url.startswith('sqlite:///'):
        return url[len('sqlite:///'):]
    return url


def init_db():
    global DB_PATH
    url = os.getenv('DATABASE_URL', 'sqlite:///backend/data/app.db')
    DB_PATH = _parse_db_url(url)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                category TEXT DEFAULT 'General',
                sku TEXT UNIQUE,
                description TEXT,
                expiry_date TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                batch_no TEXT NOT NULL,
                import_date TEXT NOT NULL,
                expiry_date TEXT NOT NULL,
                qty INTEGER NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                username TEXT,
                rating INTEGER NOT NULL,
                text TEXT,
                photo_path TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS qa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                username TEXT,
                question TEXT NOT NULL,
                answer TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                store_id TEXT,
                rating INTEGER,
                text TEXT,
                category TEXT DEFAULT 'general',
                status TEXT NOT NULL DEFAULT 'open',
                admin_reply TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT,
                customer_phone TEXT,
                customer_address TEXT,
                created_at TEXT NOT NULL,
                total REAL NOT NULL DEFAULT 0,
                status TEXT DEFAULT 'completed'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                qty INTEGER NOT NULL,
                price REAL NOT NULL,
                FOREIGN KEY(order_id) REFERENCES orders(id),
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS model_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                notes TEXT,
                horizon INTEGER,
                model TEXT,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        
        # Add new tables for enhanced retail features
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS stores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                manager TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sales_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                store_id INTEGER,
                date TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                revenue REAL NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id),
                FOREIGN KEY(store_id) REFERENCES stores(id)
            )
            """
        )
        
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                data TEXT,
                read_status INTEGER DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        
        # Alter existing tables to add missing columns (SQLite compatible way)
        try:
            cur.execute("ALTER TABLE products ADD COLUMN category TEXT DEFAULT 'General'")
        except:
            pass
        try:
            cur.execute("ALTER TABLE products ADD COLUMN sku TEXT")
        except:
            pass
        try:
            cur.execute("ALTER TABLE products ADD COLUMN description TEXT")
        except:
            pass
        try:
            cur.execute("ALTER TABLE products ADD COLUMN expiry_date TEXT")
        except:
            pass
        try:
            # Some SQLite versions do not allow non-constant defaults in ALTER TABLE.
            # Use a simple TEXT column; we always set created_at explicitly in inserts.
            cur.execute("ALTER TABLE products ADD COLUMN created_at TEXT")
        except:
            pass
        try:
            cur.execute("ALTER TABLE products ADD COLUMN stock_quantity INTEGER DEFAULT 0")
        except:
            pass
        try:
            cur.execute("ALTER TABLE products ADD COLUMN min_stock_level INTEGER DEFAULT 5")
        except:
            pass
        try:
            cur.execute("ALTER TABLE products ADD COLUMN store_id INTEGER")
        except:
            pass

        # Ensure feedback table has all expected columns even on older databases
        try:
            cur.execute("ALTER TABLE feedback ADD COLUMN store_id TEXT")
        except:
            pass
        try:
            cur.execute("ALTER TABLE feedback ADD COLUMN category TEXT DEFAULT 'general'")
        except:
            pass
        try:
            cur.execute("ALTER TABLE feedback ADD COLUMN status TEXT NOT NULL DEFAULT 'open'")
        except:
            pass
        try:
            cur.execute("ALTER TABLE feedback ADD COLUMN admin_reply TEXT")
        except:
            pass
        try:
            cur.execute("ALTER TABLE feedback ADD COLUMN created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP")
        except:
            pass

        # Seed default Tamil Nadu retail stores if none exist
        try:
            existing_store_count = cur.execute("SELECT COUNT(*) FROM stores").fetchone()[0]
        except Exception:
            existing_store_count = 0

        if existing_store_count == 0:
            default_stores = [
                ("Retail Store - Chennai", "Chennai district, Tamil Nadu", "Manager - Chennai"),
                ("Retail Store - Coimbatore", "Coimbatore district, Tamil Nadu", "Manager - Coimbatore"),
                ("Retail Store - Madurai", "Madurai district, Tamil Nadu", "Manager - Madurai"),
                ("Retail Store - Tiruchirappalli", "Tiruchirappalli district, Tamil Nadu", "Manager - Tiruchirappalli"),
                ("Retail Store - Salem", "Salem district, Tamil Nadu", "Manager - Salem"),
                ("Retail Store - Tirunelveli", "Tirunelveli district, Tamil Nadu", "Manager - Tirunelveli"),
                ("Retail Store - Erode", "Erode district, Tamil Nadu", "Manager - Erode"),
                ("Retail Store - Vellore", "Vellore district, Tamil Nadu", "Manager - Vellore"),
                ("Retail Store - Thanjavur", "Thanjavur district, Tamil Nadu", "Manager - Thanjavur"),
                ("Retail Store - Tiruppur", "Tiruppur district, Tamil Nadu", "Manager - Tiruppur"),
                ("Retail Store - Dindigul", "Dindigul district, Tamil Nadu", "Manager - Dindigul"),
                ("Retail Store - Thoothukudi", "Thoothukudi district, Tamil Nadu", "Manager - Thoothukudi"),
                ("Retail Store - Kancheepuram", "Kancheepuram district, Tamil Nadu", "Manager - Kancheepuram"),
                ("Retail Store - Nagapattinam", "Nagapattinam district, Tamil Nadu", "Manager - Nagapattinam"),
                ("Retail Store - Namakkal", "Namakkal district, Tamil Nadu", "Manager - Namakkal"),
                ("Retail Store - Karur", "Karur district, Tamil Nadu", "Manager - Karur"),
                ("Retail Store - Krishnagiri", "Krishnagiri district, Tamil Nadu", "Manager - Krishnagiri"),
                ("Retail Store - Cuddalore", "Cuddalore district, Tamil Nadu", "Manager - Cuddalore"),
                ("Retail Store - Sivaganga", "Sivaganga district, Tamil Nadu", "Manager - Sivaganga"),
                ("Retail Store - Virudhunagar", "Virudhunagar district, Tamil Nadu", "Manager - Virudhunagar"),
                ("Retail Store - Theni", "Theni district, Tamil Nadu", "Manager - Theni"),
                ("Retail Store - Villupuram", "Villupuram district, Tamil Nadu", "Manager - Villupuram"),
                ("Retail Store - Ramanathapuram", "Ramanathapuram district, Tamil Nadu", "Manager - Ramanathapuram"),
                ("Retail Store - Pudukkottai", "Pudukkottai district, Tamil Nadu", "Manager - Pudukkottai"),
                ("Retail Store - Dharmapuri", "Dharmapuri district, Tamil Nadu", "Manager - Dharmapuri"),
                ("Retail Store - Tiruvarur", "Tiruvarur district, Tamil Nadu", "Manager - Tiruvarur"),
                ("Retail Store - Nilgiris", "The Nilgiris district, Tamil Nadu", "Manager - Nilgiris"),
                ("Retail Store - Ariyalur", "Ariyalur district, Tamil Nadu", "Manager - Ariyalur"),
                ("Retail Store - Perambalur", "Perambalur district, Tamil Nadu", "Manager - Perambalur"),
                ("Retail Store - Tiruvallur", "Tiruvallur district, Tamil Nadu", "Manager - Tiruvallur"),
                ("Retail Store - Kanyakumari", "Kanyakumari district, Tamil Nadu", "Manager - Kanyakumari"),
                ("Retail Store - Tiruvannamalai", "Tiruvannamalai district, Tamil Nadu", "Manager - Tiruvannamalai"),
            ]

            now = datetime.utcnow().isoformat()
            for name, location, manager in default_stores:
                cur.execute(
                    "INSERT INTO stores (name, location, manager, created_at) VALUES (?, ?, ?, ?)",
                    (name, location, manager, now),
                )

        conn.commit()


@contextmanager
def get_conn():
    assert DB_PATH, 'DB not initialized'
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()
