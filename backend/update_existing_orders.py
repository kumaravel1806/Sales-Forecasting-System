import sqlite3

def update_existing_orders():
    conn = sqlite3.connect('data/app.db')
    cur = conn.cursor()
    
    # Update all existing orders to 'completed' as requested
    cur.execute("""
        UPDATE orders 
        SET status = 'completed'
        WHERE status IS NULL OR status = '' OR status = 'failed'
    """)
    
    updated_count = cur.rowcount
    conn.commit()
    conn.close()
    
    print(f"Updated {updated_count} orders to 'completed' status")

if __name__ == "__main__":
    update_existing_orders()
