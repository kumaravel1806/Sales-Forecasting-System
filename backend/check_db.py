import sqlite3
import os
import sys
sys.path.append(os.path.dirname(__file__))

from db import init_db, DB_PATH

def check_database():
    print('Initializing database...')
    init_db()
    print(f'DB_PATH: {DB_PATH}')
    
    # Use default path if DB_PATH is None
    db_path = DB_PATH or 'data/app.db'
    print(f'Using database path: {db_path}')
    
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # List all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print('Tables in database:')
        for table in tables:
            print(f'  {table[0]}')
        
        # Check if stores table exists specifically
        if ('stores',) in tables:
            print('\nStores table exists!')
            cursor.execute('SELECT * FROM stores')
            stores = cursor.fetchall()
            print(f'Current stores: {stores}')
        else:
            print('\nStores table does not exist!')
        
        conn.close()
    else:
        print('Database file does not exist!')

if __name__ == '__main__':
    check_database()
