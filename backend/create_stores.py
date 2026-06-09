import sqlite3
import os
from datetime import datetime

def create_stores_table_and_add_data():
    # Connect to database
    db_path = 'data/app.db'
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create stores table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            location TEXT,
            manager TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Clear existing stores
    cursor.execute('DELETE FROM stores')
    
    # Add the new stores
    store_names = [
        'namakkal', 'salem', 'karur', 'trichy', 'thanjavur', 
        'coimbatore', 'chennai', 'villupuram', 'kanchipuram', 
        'madurai', 'dindigul', 'cuddalore', 'ariyalur', 
        'thambaram', 'chengalpattu', 'velore', 'krishnagiri', 'dharmapuri'
    ]
    
    for store_name in store_names:
        cursor.execute('''
            INSERT INTO stores (name, location, manager, created_at)
            VALUES (?, ?, ?, ?)
        ''', (store_name.title(), store_name.title(), 'Store Manager', datetime.now().isoformat()))
    
    conn.commit()
    
    # Verify the stores were added
    cursor.execute('SELECT * FROM stores')
    all_stores = cursor.fetchall()
    print(f'Successfully added {len(all_stores)} stores:')
    for store in all_stores:
        print(f'  ID: {store[0]}, Name: {store[1]}, Location: {store[2]}, Manager: {store[3]}')
    
    conn.close()

if __name__ == '__main__':
    create_stores_table_and_add_data()
