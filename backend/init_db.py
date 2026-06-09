import sys
import os
sys.path.append(os.path.dirname(__file__))

from db import init_db
from check_stores import check_and_add_stores

if __name__ == '__main__':
    print('Initializing database...')
    init_db()
    print('Database initialized successfully')
    
    print('Adding stores...')
    check_and_add_stores()
    print('Stores added successfully')
