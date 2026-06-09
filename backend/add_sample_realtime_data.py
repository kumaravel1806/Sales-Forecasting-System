"""
Add Sample Data for Real-Time Dashboard Demo
This script adds sample orders, feedback, and sales data to demonstrate the dashboard
"""

import sqlite3
import os
import random
from datetime import datetime, timedelta

def add_sample_data():
    db_path = os.path.join('data', 'app.db')
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return
    
    print(f"[INFO] Connecting to database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # Add sample orders for today
        print("\n[INFO] Adding sample orders...")
        now = datetime.now()
        
        for i in range(15):
            order_time = now - timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
            total = random.uniform(100, 2000)
            
            cur.execute("""
                INSERT INTO orders (customer_name, customer_phone, customer_address, total, created_at, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                f"Customer {i+1}",
                f"+91 9876543{i:02d}",
                f"Address {i+1}, Tamil Nadu",
                total,
                order_time.isoformat(),
                'completed' if total > 500 else 'failed'
            ))
        
        print(f"[SUCCESS] Added 15 sample orders")
        
        # Add sample feedback
        print("\n[INFO] Adding sample feedback...")
        categories = ['product_quality', 'service', 'delivery', 'website']
        messages = [
            "Great product quality!",
            "Fast delivery service",
            "Excellent customer support",
            "Easy to use website",
            "Good value for money",
            "Very satisfied with purchase"
        ]
        
        for i in range(10):
            feedback_time = now - timedelta(hours=random.randint(0, 23))
            rating = random.choice([3, 4, 4, 5, 5])
            
            cur.execute("""
                INSERT INTO feedback (rating, category, text, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                rating,
                random.choice(categories),
                random.choice(messages),
                'open',
                feedback_time.isoformat()
            ))
        
        print(f"[SUCCESS] Added {cur.rowcount} sample feedback entries")
        
        # Get some products
        products = cur.execute("SELECT id, name, sku, price FROM products LIMIT 5").fetchall()
        
        if products:
            # Add sample sales data
            print("\n[INFO] Adding sample sales data...")
            stores = cur.execute("SELECT id FROM stores LIMIT 10").fetchall()
            
            if stores:
                for _ in range(20):
                    product = random.choice(products)
                    store = random.choice(stores)
                    sale_time = now - timedelta(hours=random.randint(0, 72))
                    quantity = random.randint(1, 10)
                    revenue = product[3] * quantity
                    
                    cur.execute("""
                        INSERT INTO sales_data (product_id, store_id, date, quantity, revenue, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        product[0],
                        store[0],
                        sale_time.date().isoformat(),
                        quantity,
                        revenue,
                        sale_time.isoformat()
                    ))
                
                print(f"[SUCCESS] Added 20 sample sales records")
            else:
                print("[WARN] No stores found, skipping sales data")
        else:
            print("[WARN] No products found, skipping sales data")
        
        conn.commit()
        
        # Summary
        print("\n[SUCCESS] Sample data added successfully!")
        orders_count = cur.execute('SELECT COUNT(*) FROM orders WHERE date(created_at) = date("now")').fetchone()[0]
        feedback_count = cur.execute('SELECT COUNT(*) FROM feedback WHERE date(created_at) = date("now")').fetchone()[0]
        sales_count = cur.execute('SELECT COUNT(*) FROM sales_data').fetchone()[0]
        print(f"  - Orders: {orders_count}")
        print(f"  - Feedback: {feedback_count}")
        print(f"  - Sales: {sales_count}")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 70)
    print("Adding Sample Real-Time Dashboard Data")
    print("=" * 70)
    add_sample_data()
    print("=" * 70)
    print("Complete! Refresh the dashboard to see data.")
