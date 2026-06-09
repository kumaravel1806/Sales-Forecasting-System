import sqlite3
import os
from datetime import datetime

def check_and_add_stores():
    # Initialize database first
    from db import init_db
    init_db()
    
    # Check if database exists
    db_path = 'data/app.db'
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if stores table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stores'")
        table_exists = cursor.fetchone()
        
        if table_exists:
            # Check existing stores
            cursor.execute('SELECT * FROM stores')
            existing_stores = cursor.fetchall()
            print('Existing stores:', existing_stores)
            
            # Clear existing stores
            cursor.execute('DELETE FROM stores')
            print('Cleared existing stores')
            
            # Add new stores
            store_names = [
                'namakkal', 'salem', 'karur', 'trichy', 'thanjavur', 
                'coimbatore', 'chennai', 'villupuram', 'kanchipuram', 
                'madurai', 'dindigul', 'cuddalore', 'ariyalur', 
                'thambaram', 'chengalpattu', 'velore', 'krishnagiri', 'dharmapuri'
            ]
            
            for store_name in store_names:
                cursor.execute("""
                    INSERT INTO stores (name, location, manager, created_at)
                    VALUES (?, ?, ?, ?)
                """, (store_name.title(), store_name.title(), 'Store Manager', datetime.now().isoformat()))
            
            conn.commit()
            print(f'Added {len(store_names)} new stores')
            
            # Verify the stores were added
            cursor.execute('SELECT * FROM stores')
            all_stores = cursor.fetchall()
            print('All stores after update:')
            for store in all_stores:
                print(f'  ID: {store[0]}, Name: {store[1]}, Location: {store[2]}, Manager: {store[3]}')
            
        else:
            print('Stores table does not exist')
        
        conn.close()
    else:
        print('Database does not exist')

if __name__ == '__main__':
    check_and_add_stores()
