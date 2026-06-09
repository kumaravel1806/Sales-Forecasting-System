#!/usr/bin/env python3
"""
Create test users for the retail forecasting system
"""
import sqlite3
from datetime import datetime
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(__file__))

from db import get_conn, init_db
from utils.auth import hash_password

def create_test_users():
    """Create admin and regular test users"""
    
    users = [
        {
            'email': 'admin@example.com',
            'username': 'admin',
            'password': 'password',
            'role': 'admin'
        },
        {
            'email': 'user@example.com', 
            'username': 'testuser',
            'password': 'password',
            'role': 'user'
        },
        {
            'email': 'john@example.com',
            'username': 'john',
            'password': 'password123',
            'role': 'user'
        },
        {
            'email': 'jane@example.com',
            'username': 'jane', 
            'password': 'password123',
            'role': 'user'
        }
    ]
    
    with get_conn() as conn:
        cur = conn.cursor()
        
        # Clear existing users
        cur.execute('DELETE FROM users')
        
        # Create new users
        for user in users:
            password_hash = hash_password(user['password'])
            
            try:
                cur.execute(
                    'INSERT INTO users (email, username, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
                    (user['email'], user['username'], password_hash, user['role'], datetime.utcnow().isoformat())
                )
                print(f"SUCCESS: Created user: {user['email']} (role: {user['role']})")
                
            except Exception as e:
                print(f"ERROR: Failed to create user {user['email']}: {e}")
        
        conn.commit()
        
        # Verify users were created
        users_count = cur.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        print(f"\nTotal users in database: {users_count}")
        
        # Show all users
        all_users = cur.execute('SELECT email, username, role FROM users').fetchall()
        print("\nAll users:")
        for user in all_users:
            print(f"   - {user[0]} ({user[1]}) - {user[2]}")

if __name__ == "__main__":
    print("Creating test users for retail forecasting system...")
    
    # Initialize database first
    init_db()
    print("Database initialized...")
    
    create_test_users()
    print("\nTest users created successfully!")
    print("\nLogin credentials:")
    print("   Admin: admin@example.com / password")
    print("   User:  user@example.com / password")
    print("   User:  john@example.com / password123")
    print("   User:  jane@example.com / password123")
