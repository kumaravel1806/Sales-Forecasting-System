import sqlite3

def add_status_column():
    conn = sqlite3.connect('data/app.db')
    cur = conn.cursor()
    
    try:
        cur.execute("ALTER TABLE orders ADD COLUMN status TEXT DEFAULT 'completed'")
        conn.commit()
        print("Successfully added status column to orders table")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Status column already exists")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_status_column()
