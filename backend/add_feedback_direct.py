#!/usr/bin/env python3
"""
Add sample feedback directly to database
"""

import sqlite3
from datetime import datetime

def add_sample_feedback():
    """Add sample feedback entries directly to database"""
    db_path = "backend/data/app.db"
    
    # Sample feedback data
    sample_feedback = [
        {
            "rating": 5,
            "message": "Excellent service! The staff was very helpful and the products are of great quality.",
            "category": "service",
            "store_id": "1"
        },
        {
            "rating": 4,
            "message": "Good experience overall. The store is well organized and prices are reasonable.",
            "category": "general",
            "store_id": "1"
        },
        {
            "rating": 3,
            "message": "Average experience. Some products were out of stock but the staff was helpful.",
            "category": "inventory",
            "store_id": "1"
        },
        {
            "rating": 5,
            "message": "Amazing customer service! They went above and beyond to help me find what I needed.",
            "category": "service",
            "store_id": "2"
        },
        {
            "rating": 2,
            "message": "Long waiting times and some products were expired. Needs improvement.",
            "category": "quality",
            "store_id": "2"
        }
    ]
    
    print("Adding sample feedback data directly to database...")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for i, feedback in enumerate(sample_feedback, 1):
            created_at = datetime.utcnow().isoformat()
            cursor.execute("""
                INSERT INTO feedback (user_id, store_id, rating, text, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                1,  # user_id (admin)
                feedback["store_id"],
                feedback["rating"],
                feedback["message"],
                "open",  # status
                created_at
            ))
            print(f"[SUCCESS] Feedback {i} added successfully")
        
        conn.commit()
        conn.close()
        
        print("\nSample feedback data added successfully!")
        print("Now you can test the feedback management page at: http://localhost:8000/feedback_management.html")
        print("Login with: admin@example.com / password")
        
    except Exception as e:
        print(f"[ERROR] Failed to add feedback: {e}")

if __name__ == "__main__":
    add_sample_feedback()
