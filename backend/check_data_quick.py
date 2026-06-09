from db import get_conn, init_db

# Initialize database first
init_db()

with get_conn() as conn:
    cur = conn.cursor()
    
    products = cur.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    batches = cur.execute("SELECT COUNT(*) FROM inventory_batches").fetchone()[0]
    orders = cur.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    users = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    
    print(f"Database Status:")
    print(f"  Products: {products}")
    print(f"  Inventory Batches: {batches}")
    print(f"  Orders: {orders}")
    print(f"  Users: {users}")
    
    if products > 0:
        print(f"\n✅ Database has products!")
        if batches == 0:
            print(f"⚠️  No inventory batches - run add_sample_batches.py")
    else:
        print(f"\n❌ No products - need to add data!")
