"""
Setup Tamil Nadu District Stores
This script clears existing stores and adds 32 stores for Tamil Nadu districts
"""

import sqlite3
import os
from datetime import datetime

# 32 Tamil Nadu Districts
TAMILNADU_DISTRICTS = [
    "Ariyalur", "Chengalpattu", "Chennai", "Coimbatore", "Cuddalore",
    "Dharmapuri", "Dindigul", "Erode", "Kallakurichi", "Kancheepuram",
    "Kanyakumari", "Karur", "Krishnagiri", "Madurai", "Nagapattinam",
    "Namakkal", "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram",
    "Ranipet", "Salem", "Sivaganga", "Tenkasi", "Thanjavur",
    "Theni", "Thoothukudi", "Tiruchirappalli", "Tirunelveli", "Tiruppur",
    "Tiruvallur", "Vellore"
]

def setup_stores():
    # Get database path
    db_path = os.path.join('backend', 'data', 'app.db')
    
    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found at {db_path}")
        return
    
    print(f"[INFO] Connecting to database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        # Clear existing stores
        print("[INFO] Removing existing stores...")
        cur.execute('DELETE FROM stores')
        conn.commit()
        print(f"[SUCCESS] Cleared {cur.rowcount} existing stores")
        
        # Add Tamil Nadu district stores
        print(f"\n[INFO] Adding {len(TAMILNADU_DISTRICTS)} Tamil Nadu district stores...")
        
        created_at = datetime.utcnow().isoformat()
        
        for district in TAMILNADU_DISTRICTS:
            store_name = f"{district} Store"
            location = f"{district} District, Tamil Nadu"
            manager = f"Manager - {district}"
            
            cur.execute(
                'INSERT INTO stores (name, location, manager, created_at) VALUES (?, ?, ?, ?)',
                (store_name, location, manager, created_at)
            )
            store_id = cur.lastrowid
            print(f"  [OK] Added: {store_name} (ID: {store_id})")
        
        conn.commit()
        
        # Verify
        count = cur.execute('SELECT COUNT(*) FROM stores').fetchone()[0]
        print(f"\n[SUCCESS] Successfully added {count} stores!")
        
        # Show all stores
        print("\n[LIST] All Tamil Nadu District Stores:")
        stores = cur.execute('SELECT id, name, location FROM stores ORDER BY name').fetchall()
        for store_id, name, location in stores:
            print(f"  {store_id:2d}. {name:25s} - {location}")
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    print("=" * 70)
    print("Tamil Nadu District Stores Setup")
    print("=" * 70)
    setup_stores()
    print("=" * 70)
    print("Setup complete!")
