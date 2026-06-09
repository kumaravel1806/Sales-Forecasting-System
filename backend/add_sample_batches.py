#!/usr/bin/env python3
"""
Quick script to add sample inventory batches for testing dashboard counts
"""
from db import get_conn, init_db
from datetime import datetime, timedelta
import random

# Initialize database
init_db()

def add_sample_batches():
    """Add sample inventory batches with various expiry dates"""
    
    with get_conn() as conn:
        cur = conn.cursor()
        
        # First check if we have products
        products = cur.execute('SELECT id, name, price FROM products LIMIT 20').fetchall()
        
        if not products:
            print("ERROR: No products found in database!")
            print("   Please add products first via admin panel or seed script")
            return
        
        print(f"SUCCESS: Found {len(products)} products")
        print(f"\nAdding sample inventory batches...\n")
        
        today = datetime.now().date()
        batches_added = 0
        
        # Add batches with different expiry scenarios
        for i, product in enumerate(products[:15]):  # Use first 15 products
            product_id, name, price = product
            
            # Scenario 1: Already expired (20% of products)
            if i % 5 == 0:
                expiry_date = today - timedelta(days=random.randint(5, 30))
                qty = random.randint(10, 50)
                batch_no = f"EXPIRED-{i:03d}"
                
                cur.execute('''
                    INSERT INTO inventory_batches (product_id, batch_no, expiry_date, qty, import_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (product_id, batch_no, expiry_date.isoformat(), qty, datetime.now().isoformat()))
                
                print(f"  [EXPIRED] {name[:30]:30} | Batch: {batch_no} | Expired {(today - expiry_date).days} days ago | Qty: {qty}")
                batches_added += 1
            
            # Scenario 2: Near expiry (expires in next 7 days) (30% of products)
            elif i % 3 == 0:
                expiry_date = today + timedelta(days=random.randint(1, 7))
                qty = random.randint(20, 100)
                batch_no = f"EXPIRING-{i:03d}"
                
                cur.execute('''
                    INSERT INTO inventory_batches (product_id, batch_no, expiry_date, qty, import_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (product_id, batch_no, expiry_date.isoformat(), qty, datetime.now().isoformat()))
                
                days_left = (expiry_date - today).days
                print(f"  [WARNING] Near Expiry: {name[:30]:30} | Batch: {batch_no} | Expires in {days_left} days | Qty: {qty}")
                batches_added += 1
            
            # Scenario 3: Good stock (expires in 30+ days)
            else:
                expiry_date = today + timedelta(days=random.randint(30, 180))
                qty = random.randint(50, 200)
                batch_no = f"GOOD-{i:03d}"
                
                cur.execute('''
                    INSERT INTO inventory_batches (product_id, batch_no, expiry_date, qty, import_date)
                    VALUES (?, ?, ?, ?, ?)
                ''', (product_id, batch_no, expiry_date.isoformat(), qty, datetime.now().isoformat()))
                
                days_left = (expiry_date - today).days
                print(f"  [OK] Good: {name[:30]:30} | Batch: {batch_no} | Expires in {days_left} days | Qty: {qty}")
                batches_added += 1
        
        # Also update some products to have low stock
        print(f"\n\nUpdating product stock levels...\n")
        
        for i, product in enumerate(products[:10]):
            product_id = product[0]
            
            if i % 3 == 0:  # Critical stock (0)
                cur.execute('UPDATE products SET stock_quantity = 0 WHERE id = ?', (product_id,))
                print(f"  [CRITICAL] {product[1][:40]:40} | Stock: 0")
            elif i % 2 == 0:  # Low stock (below minimum)
                stock = random.randint(1, 5)
                cur.execute('UPDATE products SET stock_quantity = ?, min_stock_level = ? WHERE id = ?', 
                          (stock, 10, product_id))
                print(f"  [LOW] Low Stock: {product[1][:40]:40} | Stock: {stock} (Min: 10)")
            else:  # Good stock
                stock = random.randint(50, 200)
                cur.execute('UPDATE products SET stock_quantity = ?, min_stock_level = ? WHERE id = ?', 
                          (stock, 10, product_id))
                print(f"  [GOOD] {product[1][:40]:40} | Stock: {stock}")
        
        conn.commit()
        
        print(f"\n" + "="*70)
        print(f"SUCCESS: Added {batches_added} inventory batches!")
        print(f"="*70)
        
        # Show summary
        expired_count = cur.execute('''
            SELECT COUNT(*) FROM inventory_batches 
            WHERE qty > 0 AND date(expiry_date) < date('now')
        ''').fetchone()[0]
        
        near_expiry_count = cur.execute('''
            SELECT COUNT(*) FROM inventory_batches 
            WHERE qty > 0 AND date(expiry_date) BETWEEN date('now') AND date('now', '+7 days')
        ''').fetchone()[0]
        
        critical_stock = cur.execute('SELECT COUNT(*) FROM products WHERE stock_quantity = 0').fetchone()[0]
        low_stock = cur.execute('SELECT COUNT(*) FROM products WHERE stock_quantity > 0 AND stock_quantity < min_stock_level').fetchone()[0]
        
        print(f"\nDashboard Counts Preview:")
        print(f"  - Critical Stock (0 units): {critical_stock}")
        print(f"  - Low Stock (below minimum): {low_stock}")
        print(f"  - Near Expiry (7 days): {near_expiry_count} batches")
        print(f"  - Expired: {expired_count} batches")
        print(f"\nNow open the dashboard to see these counts!")
        print(f"   http://localhost:8000/admin_dashboard.html")
        print(f"="*70)

if __name__ == "__main__":
    print("="*70)
    print("SAMPLE INVENTORY BATCH GENERATOR")
    print("="*70)
    print("\nThis will add sample inventory batches to test dashboard counts.")
    print("The batches will include:")
    print("  - Expired items (already past expiry date)")
    print("  - Near expiry items (expiring in next 7 days)")
    print("  - Good items (expiring in 30+ days)")
    print("="*70)
    
    try:
        add_sample_batches()
    except Exception as e:
        print(f"\nERROR: {e}")
        print("\nMake sure:")
        print("  1. Database exists")
        print("  2. Products table has data")
        print("  3. You're in the correct directory")
