import sqlite3

def check_schema():
    conn = sqlite3.connect('data/app.db')
    cur = conn.cursor()
    
    cur.execute("PRAGMA table_info(orders)")
    columns = cur.fetchall()
    
    print("Orders table schema:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    conn.close()

if __name__ == "__main__":
    check_schema()
