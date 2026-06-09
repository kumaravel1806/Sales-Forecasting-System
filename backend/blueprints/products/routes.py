from flask import Blueprint, jsonify, request
from db import get_conn
from datetime import datetime

bp = Blueprint("products", __name__)


@bp.get("/")
def list_products():
    with get_conn() as conn:
        cur = conn.cursor()
        rows = cur.execute('SELECT id, name, price, category, sku, description, expiry_date, stock_quantity, min_stock_level FROM products ORDER BY id ASC').fetchall()
    items = [{
        "id": r[0], 
        "name": r[1], 
        "price": float(r[2]), 
        "category": r[3], 
        "sku": r[4], 
        "description": r[5], 
        "expiry_date": r[6],
        "stock_quantity": r[7] or 0,
        "min_stock_level": r[8] or 5
    } for r in rows]
    return jsonify({"success": True, "data": items, "meta": {}})


@bp.post("/")
def create_product():
    """Add a new product with auto-unique SKU handling"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "meta": {"error": "No data provided"}}), 400
        
        name = data.get('name')
        price = data.get('price')
        
        if not name or price is None:
            return jsonify({"success": False, "meta": {"error": "Name and price are required"}}), 400
        
        category = data.get('category', 'General')
        sku = data.get('sku', '')
        description = data.get('description', '')
        expiry_date = data.get('expiry_date')
        if expiry_date == '':
            expiry_date = None
        stock_quantity = int(data.get('stock_quantity') or 0)
        min_stock_level = int(data.get('min_stock_level') or 5)
        store_id = data.get('store_id')
        
        # Auto-generate unique SKU if duplicate or empty
        with get_conn() as conn:
            cur = conn.cursor()
            
            if not sku:
                # Generate SKU from category and timestamp
                import time
                prefix = category[:4].upper() if category else 'PROD'
                sku = f"{prefix}-{int(time.time())}"
            else:
                # Check if SKU exists
                existing = cur.execute('SELECT id FROM products WHERE sku = ?', (sku,)).fetchone()
                if existing:
                    # Make it unique by appending timestamp
                    import time
                    sku = f"{sku}-{int(time.time() % 10000)}"
            
            cur.execute(
                '''INSERT INTO products 
                (name, price, category, sku, description, expiry_date, stock_quantity, min_stock_level, store_id, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (name, float(price), category, sku, description, expiry_date, stock_quantity, min_stock_level, store_id, datetime.utcnow().isoformat())
            )
            product_id = cur.lastrowid
            conn.commit()
        
        return jsonify({
            "success": True, 
            "data": {
                "id": product_id,
                "name": name,
                "price": float(price),
                "category": category,
                "sku": sku,
                "stock_quantity": stock_quantity,
                "min_stock_level": min_stock_level
            }, 
            "meta": {"message": f"Product added successfully with SKU: {sku}"}
        })
    except Exception as e:
        print(f"ERROR creating product: {e}")
        import traceback
        traceback.print_exc()
        error_msg = str(e)
        if "UNIQUE constraint failed" in error_msg:
            error_msg = "SKU already exists. Please use a different SKU or leave it empty for auto-generation."
        return jsonify({"success": False, "meta": {"error": error_msg}}), 500


@bp.put("/<int:product_id>")
@bp.patch("/<int:product_id>")
def update_product(product_id):
    """Update product details"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "meta": {"error": "No data provided"}}), 400
        
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Check if product exists
            product = cur.execute('SELECT id FROM products WHERE id = ?', (product_id,)).fetchone()
            if not product:
                return jsonify({"success": False, "meta": {"error": "Product not found"}}), 404
            
            # Build UPDATE query dynamically
            update_fields = []
            values = []
            
            if 'name' in data:
                update_fields.append('name = ?')
                values.append(data['name'])
            if 'price' in data:
                update_fields.append('price = ?')
                values.append(float(data['price']))
            if 'category' in data:
                update_fields.append('category = ?')
                values.append(data['category'])
            if 'sku' in data:
                update_fields.append('sku = ?')
                values.append(data['sku'])
            if 'description' in data:
                update_fields.append('description = ?')
                values.append(data['description'])
            if 'expiry_date' in data:
                update_fields.append('expiry_date = ?')
                values.append(data['expiry_date'] if data['expiry_date'] else None)
            if 'stock_quantity' in data:
                update_fields.append('stock_quantity = ?')
                values.append(int(data['stock_quantity']))
            if 'min_stock_level' in data:
                update_fields.append('min_stock_level = ?')
                values.append(int(data['min_stock_level']))
            
            if not update_fields:
                return jsonify({"success": False, "meta": {"error": "No fields to update"}}), 400
            
            values.append(product_id)
            query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ?"
            cur.execute(query, values)
            conn.commit()
        
        return jsonify({"success": True, "meta": {"message": "Product updated successfully"}})
        
    except Exception as e:
        print(f"ERROR updating product: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500


@bp.delete("/<int:product_id>")
def delete_product(product_id):
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute('DELETE FROM products WHERE id = ?', (product_id,))
            if cur.rowcount == 0:
                return jsonify({"success": False, "meta": {"error": "Product not found"}}), 404
            conn.commit()
        
        return jsonify({"success": True, "meta": {"message": "Product deleted successfully"}})
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500


@bp.post("/<int:product_id>/restock")
def restock_product(product_id):
    """Update product stock quantity"""
    try:
        data = request.get_json()
        if not data or 'stock_quantity' not in data:
            return jsonify({"success": False, "meta": {"error": "Stock quantity required"}}), 400
        
        new_stock = data['stock_quantity']
        if not isinstance(new_stock, int) or new_stock < 0:
            return jsonify({"success": False, "meta": {"error": "Invalid stock quantity"}}), 400
        
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Check if product exists
            product = cur.execute('SELECT name FROM products WHERE id = ?', (product_id,)).fetchone()
            if not product:
                return jsonify({"success": False, "meta": {"error": "Product not found"}}), 404
            
            # Update stock quantity
            cur.execute('UPDATE products SET stock_quantity = ? WHERE id = ?', (new_stock, product_id))
            conn.commit()
            
            # Track activity
            try:
                cur.execute('''
                    INSERT INTO notifications (type, title, message, data, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    'product_restocked',
                    'Product Restocked',
                    f'Product "{product[0]}" has been restocked to {new_stock} units',
                    f'{{"product_id": {product_id}, "product_name": "{product[0]}", "new_stock": {new_stock}}}',
                    datetime.utcnow().isoformat()
                ))
                conn.commit()
            except:
                pass
        
        return jsonify({
            "success": True, 
            "data": {
                "product_id": product_id,
                "new_stock": new_stock
            }, 
            "meta": {"message": "Product restocked successfully"}
        })
    
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500
