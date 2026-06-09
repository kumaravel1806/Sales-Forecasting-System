import sqlite3

def check_orders():
    conn = sqlite3.connect('data/app.db')
    cur = conn.cursor()
    
    cur.execute("SELECT id, total, status FROM orders ORDER BY created_at DESC LIMIT 5")
    orders = cur.fetchall()
    
    print("Recent orders:")
    for order in orders:
        print(f"  Order #{order[0]}: total={order[1]}, status='{order[2]}'")
    
    conn.close()

if __name__ == "__main__":
    check_orders()
