import os
from datetime import datetime, timedelta
try:
    from db import init_db, get_conn  # when running from backend/ cwd
except Exception:  # pragma: no cover
    from backend.db import init_db, get_conn  # when running as module


def main():
    init_db()
    with get_conn() as conn:
        cur = conn.cursor()
        # Seed products
        products = [
            ("Sample Milk 500ml", 1.99),
            ("Sample Bread Loaf", 0.99),
            ("Organic Eggs (12)", 2.49),
        ]
        for name, price in products:
            cur.execute('INSERT INTO products(name, price) VALUES(?, ?)', (name, price))
        # Seed inventory batches FEFO
        today = datetime.utcnow().date()
        pid_rows = cur.execute('SELECT id, name FROM products').fetchall()
        for pid, name in pid_rows:
            for i in range(1, 4):
                import_date = (today - timedelta(days=7*i)).isoformat()
                expiry_date = (today + timedelta(days=10*i)).isoformat()
                cur.execute(
                    'INSERT INTO inventory_batches(product_id, batch_no, import_date, expiry_date, qty) VALUES(?,?,?,?,?)',
                    (pid, f"B{pid}-{i}", import_date, expiry_date, 10*i)
                )
        conn.commit()
    print('Seeded products and inventory batches.')


if __name__ == '__main__':
    main()
