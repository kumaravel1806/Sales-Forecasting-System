import io
import os
import time
from typing import Dict, Any

import numpy as np
import pandas as pd
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
import os
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeClassifier
from utils.data_cleaning import clean_dataframe, summarize_dataframe, analyze_data_quality
from utils.auth import admin_required
from db import get_conn
from datetime import datetime, timedelta

bp = Blueprint("admin", __name__)

ALLOWED_EXT = {".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet", ".csv.gz", ".tsv.gz", ".json.gz", ".parquet.gz"}


def _ensure_dirs():
    base = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    uploads = os.path.abspath(os.path.join(base, "uploads"))
    cleaned = os.path.abspath(os.path.join(base, "cleaned"))
    os.makedirs(uploads, exist_ok=True)
    os.makedirs(cleaned, exist_ok=True)
    return uploads, cleaned


@bp.post("/upload")
@admin_required
def upload_and_clean():
    if "file" not in request.files:
        return jsonify({"success": False, "data": None, "meta": {"error": "file_missing"}}), 400

    f = request.files["file"]
    filename = secure_filename(f.filename or "")
    if not filename:
        return jsonify({"success": False, "data": None, "meta": {"error": "filename_required"}}), 400

    # Support double extensions for gzip
    base, ext1 = os.path.splitext(filename)
    ext2 = os.path.splitext(base)[1].lower()
    ext = (ext2 + ext1.lower()) if ext1.lower() == ".gz" else ext1.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"success": False, "data": None, "meta": {"error": "unsupported_extension", "allowed": list(ALLOWED_EXT)}}), 400

    uploads_dir, cleaned_dir = _ensure_dirs()
    ts = int(time.time())
    saved_path = os.path.join(uploads_dir, f"{ts}_{filename}")
    f.save(saved_path)

    rules: Dict[str, Any] = {}
    if request.form.get("rules"):
        try:
            import json
            rules = json.loads(request.form["rules"]) or {}
        except Exception:
            return jsonify({"success": False, "data": None, "meta": {"error": "invalid_rules_json"}}), 400

    try:
        if ext in (".csv", ".csv.gz"):
            df = pd.read_csv(saved_path)
        elif ext in (".tsv", ".tsv.gz"):
            df = pd.read_csv(saved_path, sep='\t')
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(saved_path)
        elif ext in (".json", ".json.gz"):
            df = pd.read_json(saved_path, lines=False)
        elif ext in (".parquet", ".parquet.gz"):
            df = pd.read_parquet(saved_path)
        else:
            return jsonify({"success": False, "data": None, "meta": {"error": "unsupported_extension_runtime"}}), 400
    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": "parse_failed", "detail": str(e)}}), 400

    # Default cleaning rules
    rules = {
        "lowercase_columns": True,
        "trim_whitespace": True,
        "drop_threshold": 0.8,
        "fill_numeric": "mean",
        "fill_categorical": "mode",
        "remove_duplicates": True
    }
    cleaned_df = clean_dataframe(df, rules)
    summary_before = summarize_dataframe(df)
    summary_after = summarize_dataframe(cleaned_df)
    
    # Analyze data quality with automatic metrics
    quality_before = analyze_data_quality(df)
    quality_after = analyze_data_quality(cleaned_df)

    cleaned_name = f"{ts}_cleaned_{os.path.splitext(filename)[0]}.csv"
    cleaned_path = os.path.join(cleaned_dir, cleaned_name)
    try:
        cleaned_df.to_csv(cleaned_path, index=False)
    except Exception:
        cleaned_path = None

    return jsonify({
        "success": True,
        "data": {
            "uploaded_path": saved_path,
            "cleaned_path": cleaned_path,
            "summary_before": summary_before,
            "summary_after": summary_after,
            "quality_analysis_before": quality_before,
            "quality_analysis_after": quality_after,
            "improvement": {
                "quality_score_before": quality_before.get("quality_score", "Unknown"),
                "quality_score_after": quality_after.get("quality_score", "Unknown"),
                "missing_reduction": quality_before.get("missing_percentage", 0) - quality_after.get("missing_percentage", 0),
                "duplicate_reduction": quality_before.get("duplicate_rows", 0) - quality_after.get("duplicate_rows", 0)
            }
        },
        "meta": {
            "rows_in": summary_before.get("rows"), 
            "rows_out": summary_after.get("rows"),
            "quality_improved": quality_after.get("quality_score") != quality_before.get("quality_score")
        }
    })

@bp.route("/clean-data", methods=["POST"])
def clean_data():
    """Clean uploaded dataset - simplified without auth for testing"""
    if "file" not in request.files:
        return jsonify({"success": False, "data": None, "meta": {"error": "file_missing"}}), 400

    f = request.files["file"]
    filename = secure_filename(f.filename or "")
    if not filename:
        return jsonify({"success": False, "data": None, "meta": {"error": "filename_required"}}), 400

    # Support double extensions for gzip
    base, ext1 = os.path.splitext(filename)
    ext2 = os.path.splitext(base)[1].lower()
    ext = (ext2 + ext1.lower()) if ext1.lower() == ".gz" else ext1.lower()
    if ext not in ALLOWED_EXT:
        return jsonify({"success": False, "data": None, "meta": {"error": "unsupported_extension", "allowed": list(ALLOWED_EXT)}}), 400

    uploads_dir, cleaned_dir = _ensure_dirs()
    ts = int(time.time())
    saved_path = os.path.join(uploads_dir, f"{ts}_{filename}")
    f.save(saved_path)

    try:
        # Load the data
        if ext in [".csv", ".csv.gz"]:
            df = pd.read_csv(saved_path)
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(saved_path)
        elif ext in [".json", ".json.gz"]:
            df = pd.read_json(saved_path)
        elif ext in [".parquet", ".parquet.gz"]:
            df = pd.read_parquet(saved_path)
        else:
            return jsonify({"success": False, "data": None, "meta": {"error": "unsupported_format"}}), 400

        # Analyze before cleaning
        summary_before = summarize_dataframe(df)
        quality_before = analyze_data_quality(df)

        # Clean the data with default rules
        cleaning_rules = {
            "lowercase_columns": True,
            "trim_whitespace": True,
            "drop_threshold": 0.8,  # Drop columns with >80% missing values
            "fill_numeric": "mean",
            "fill_categorical": "mode",
            "remove_duplicates": True
        }
        df_cleaned = clean_dataframe(df, cleaning_rules)

        # Analyze after cleaning
        summary_after = summarize_dataframe(df_cleaned)
        quality_after = analyze_data_quality(df_cleaned)

        # Save cleaned data
        cleaned_path = os.path.join(cleaned_dir, f"cleaned_{ts}_{filename}")
        if ext in [".csv", ".csv.gz"]:
            df_cleaned.to_csv(cleaned_path, index=False)
        elif ext in [".xlsx", ".xls"]:
            df_cleaned.to_excel(cleaned_path, index=False)
        elif ext in [".json", ".json.gz"]:
            df_cleaned.to_json(cleaned_path, orient='records')
        elif ext in [".parquet", ".parquet.gz"]:
            df_cleaned.to_parquet(cleaned_path, index=False)

        # Convert numpy types to Python types for JSON serialization
        def convert_numpy_types(obj):
            if hasattr(obj, 'item'):
                return obj.item()
            elif isinstance(obj, dict):
                return {k: convert_numpy_types(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_numpy_types(v) for v in obj]
            else:
                return obj
        
        response_data = {
            "success": True,
            "data": {
                "original_file": saved_path,
                "cleaned_file": cleaned_path,
                "before": {
                    "summary": convert_numpy_types(summary_before),
                    "quality": convert_numpy_types(quality_before)
                },
                "after": {
                    "summary": convert_numpy_types(summary_after),
                    "quality": convert_numpy_types(quality_after)
                },
                "improvement": {
                    "quality_score_before": str(quality_before.get("quality_score", "Unknown")),
                    "quality_score_after": str(quality_after.get("quality_score", "Unknown")),
                    "missing_reduction": float(quality_before.get("missing_percentage", 0) - quality_after.get("missing_percentage", 0)),
                    "duplicate_reduction": int(quality_before.get("duplicate_rows", 0) - quality_after.get("duplicate_rows", 0))
                }
            },
            "meta": {
                "rows_in": int(summary_before.get("rows", 0)), 
                "rows_out": int(summary_after.get("rows", 0)),
                "quality_improved": quality_after.get("quality_score") != quality_before.get("quality_score")
            }
        }
        
        return jsonify(response_data)

    except Exception as e:
        return jsonify({"success": False, "data": None, "meta": {"error": str(e)}}), 500

@bp.route("/visualize-data", methods=["POST"])
def visualize_dataset():
    """Generate automatic charts and analysis for any uploaded dataset with XGBoost/ARIMA"""
    try:
        from .visualizer import process_uploaded_file
        
        if 'file' not in request.files:
            return jsonify({"success": False, "meta": {"error": "No file uploaded"}})
        
        file = request.files['file']
        if not file.filename:
            return jsonify({"success": False, "meta": {"error": "No file selected"}})
        
        print(f"[VISUALIZER] Processing file: {file.filename}")
        
        # Get chart and analysis preferences
        chart_types = request.form.get('chart_types', '["line","bar","pie","scatter"]')
        analysis_types = request.form.get('analysis_types', '["summary","trends","outliers","forecast"]')
        
        import json
        try:
            chart_types = json.loads(chart_types)
            analysis_types = json.loads(analysis_types)
        except:
            chart_types = ["line", "bar", "pie", "scatter"]
            analysis_types = ["summary", "trends", "outliers", "forecast"]
        
        # Use the new visualizer module
        result = process_uploaded_file(file, chart_types, analysis_types)
        return jsonify(result)
        
    except Exception as e:
        print(f"[VISUALIZER] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500


@bp.route("/historical-sales", methods=["GET"])
@admin_required
def historical_sales():
    """Return historical sales time series for different periods.

    Query param:
      period: one of "48h", "30d", "60d", "365d" (default "48h").

    Uses the orders table and groups:
      - by HOUR for 48h
      - by DAY for 30d / 60d / 365d
    """
    try:
      period = (request.args.get("period") or "48h").lower()

      now = datetime.utcnow()
      if period == "30d":
          start = now - timedelta(days=30)
          bucket = "day"
      elif period == "60d":
          start = now - timedelta(days=60)
          bucket = "day"
      elif period == "365d":
          start = now - timedelta(days=365)
          bucket = "day"
      else:
          # default 48 hours
          start = now - timedelta(hours=48)
          bucket = "hour"

      with get_conn() as conn:
          cur = conn.cursor()
          cur.execute(
              """
              SELECT created_at, total
              FROM orders
              WHERE created_at >= ?
              ORDER BY created_at ASC
              """,
              (start.isoformat(),),
          )
          rows = cur.fetchall()

      # Aggregate into buckets
      from collections import OrderedDict

      buckets = OrderedDict()
      for created_at, total in rows:
          if not created_at:
              continue
          try:
              dt = datetime.fromisoformat(created_at)
          except Exception:
              # Try to parse common sqlite style "YYYY-MM-DD HH:MM:SS"
              try:
                  dt = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
              except Exception:
                  continue

          if bucket == "hour":
              key = dt.replace(minute=0, second=0, microsecond=0)
              label = key.strftime("%d %b %H:%M")
          else:
              key = dt.date()
              label = key.strftime("%d %b %Y")

          if label not in buckets:
              buckets[label] = 0.0
          buckets[label] += float(total or 0.0)

      dates = list(buckets.keys())
      values = list(buckets.values())

      ml_values = values
      try:
          if len(values) >= 5:
              X = np.arange(len(values), dtype=float).reshape(-1, 1)
              y = np.array(values, dtype=float)
              model = RandomForestRegressor(
                  n_estimators=50,
                  random_state=42,
              )
              model.fit(X, y)
              ml_values = model.predict(X).tolist()
      except Exception:
          ml_values = values

      if ml_values:
          max_val = max(ml_values) or 1.0
          ratios = [v / max_val for v in ml_values]
      else:
          max_val = 1.0
          ratios = []

      time_series = {
          "date_column": "created_at",
          "value_column": "total",
          "dates": dates,
          "values": ml_values,
          "ratios": ratios,
      }

      total_sales = float(sum(values)) if values else 0.0
      order_count = len(rows)

      # Simple ML-based sales quality suggestion using a small decision tree
      sales_quality = "Average"
      try:
          if values:
              arr = np.array(values, dtype=float)
              x_idx = np.arange(len(arr), dtype=float)
              if len(arr) > 1:
                  # slope of simple linear fit as a trend feature
                  slope = np.polyfit(x_idx, arr, 1)[0]
              else:
                  slope = 0.0

              feat = np.array([[arr.mean(), arr.std() or 0.0, arr.max() or 0.0, slope]])

              # Tiny synthetic training set for the tree
              X_train = np.array([
                  [100.0, 10.0, 150.0, -1.0],  # declining / low
                  [300.0, 50.0, 400.0, 0.0],   # stable / medium
                  [800.0, 120.0, 1000.0, 1.0], # high and growing
              ])
              y_train = np.array([0, 1, 2])  # 0=Bad,1=Average,2=Good

              clf = DecisionTreeClassifier(max_depth=2, random_state=42)
              clf.fit(X_train, y_train)
              pred = int(clf.predict(feat)[0])
              label_map = {0: "Bad", 1: "Average", 2: "Good"}
              sales_quality = label_map.get(pred, "Average")
      except Exception:
          sales_quality = "Average"

      summary = {
          "total_sales": total_sales,
          "order_count": order_count,
          "period": period,
          "sales_quality": sales_quality,
      }

      return jsonify({
          "success": True,
          "data": {
              "time_series": time_series,
              "summary": summary,
          },
          "meta": {},
      })

    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500

@bp.route("/download-cleaned/<filename>", methods=["GET"])
def download_cleaned_file(filename):
    """Download cleaned dataset file"""
    try:
        uploads_dir, cleaned_dir = _ensure_dirs()
        file_path = os.path.join(cleaned_dir, filename)
        
        print(f"Looking for file: {file_path}")
        print(f"File exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            # Try to find a similar file
            if os.path.exists(cleaned_dir):
                files = os.listdir(cleaned_dir)
                print(f"Available files: {files}")
                
                # Look for files containing the base filename
                base_name = filename.replace('cleaned_', '').replace('.csv', '')
                matching_files = [f for f in files if base_name in f or filename in f]
                
                if matching_files:
                    # Use the most recent matching file
                    matching_files.sort(reverse=True)
                    file_path = os.path.join(cleaned_dir, matching_files[0])
                    print(f"Using matching file: {file_path}")
                else:
                    return jsonify({
                        "success": False, 
                        "meta": {
                            "error": f"File not found: {filename}",
                            "available_files": files[:10]  # Show first 10 files
                        }
                    }), 404
            else:
                return jsonify({"success": False, "meta": {"error": "Cleaned directory not found"}}), 404
        
        from flask import send_file
        return send_file(file_path, as_attachment=True, download_name=f"cleaned_dataset.csv")
        
    except Exception as e:
        print(f"Download error: {str(e)}")
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500

@bp.route("/download-latest-cleaned", methods=["GET"])
def download_latest_cleaned():
    """Download the most recent cleaned dataset"""
    try:
        uploads_dir, cleaned_dir = _ensure_dirs()
        
        if not os.path.exists(cleaned_dir):
            return jsonify({"success": False, "meta": {"error": "No cleaned files available"}}), 404
        
        files = os.listdir(cleaned_dir)
        if not files:
            return jsonify({"success": False, "meta": {"error": "No cleaned files found"}}), 404
        
        # Get the most recent file
        files.sort(reverse=True)
        latest_file = files[0]
        file_path = os.path.join(cleaned_dir, latest_file)
        
        print(f"Downloading latest file: {file_path}")
        
        from flask import send_file
        return send_file(file_path, as_attachment=True, download_name="latest_cleaned_dataset.csv")
        
    except Exception as e:
        print(f"Latest download error: {str(e)}")
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500

@bp.route("/products/add", methods=["POST"])
@admin_required
def add_product():
    """Add a new product"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        price = float(data.get('price', 0))
        category = data.get('category', 'General').strip()
        sku = data.get('sku', '').strip() or None
        description = data.get('description', '').strip() or None
        
        if not name or price <= 0:
            return jsonify({"success": False, "meta": {"error": "Name and valid price required"}})
        
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO products (name, price, category, sku, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, price, category, sku, description, datetime.utcnow().isoformat()))
            product_id = cur.lastrowid
            conn.commit()
        
        return jsonify({
            "success": True,
            "data": {"product_id": product_id, "name": name, "price": price},
            "meta": {}
        })
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/products/list", methods=["GET"])
def list_products():
    """List all products (public endpoint for shop)"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, name, price, category, sku, description, created_at
                FROM products
                ORDER BY created_at DESC
            """)
            rows = cur.fetchall()
        
        products = []
        for row in rows:
            products.append({
                "id": row[0],
                "name": row[1],
                "price": float(row[2]),
                "category": row[3],
                "sku": row[4],
                "description": row[5],
                "created_at": row[6]
            })
        
        return jsonify({
            "success": True,
            "data": products,
            "meta": {"total": len(products)}
        })
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/stores/add", methods=["POST"])
@admin_required
def add_store():
    """Add a new store"""
    try:
        data = request.get_json()
        name = data.get('name', '').strip()
        location = data.get('location', '').strip() or None
        manager = data.get('manager', '').strip() or None
        
        if not name:
            return jsonify({"success": False, "meta": {"error": "Store name required"}})
        
        # Insert store into database
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO stores (name, location, manager, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (name, location, manager, datetime.utcnow().isoformat())
            )
            store_id = cur.lastrowid
            conn.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "id": store_id,
                "name": name,
                "location": location,
                "manager": manager
            },
            "meta": {"message": f"Store '{name}' added successfully"}
        })
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/feedback/<int:feedback_id>/delete", methods=["DELETE"])
@admin_required
def delete_feedback(feedback_id):
    """Delete a feedback entry"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            # Check if feedback exists
            cur.execute("SELECT id FROM feedback WHERE id = ?", (feedback_id,))
            if not cur.fetchone():
                return jsonify({"success": False, "meta": {"error": "Feedback not found"}}), 404
            
            # Delete feedback
            cur.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
            conn.commit()
        
        return jsonify({
            "success": True,
            "meta": {"message": "Feedback deleted successfully"}
        })
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500

@bp.route("/feedback/<int:feedback_id>/respond", methods=["POST"])
@admin_required
def respond_feedback(feedback_id):
    """Add admin response to feedback"""
    try:
        data = request.get_json()
        admin_reply = data.get('admin_reply', '').strip()
        
        if not admin_reply:
            return jsonify({"success": False, "meta": {"error": "Response text required"}}), 400
        
        with get_conn() as conn:
            cur = conn.cursor()
            # Check if feedback exists
            cur.execute("SELECT id FROM feedback WHERE id = ?", (feedback_id,))
            if not cur.fetchone():
                return jsonify({"success": False, "meta": {"error": "Feedback not found"}}), 404
            
            # Update feedback with admin reply
            cur.execute(
                "UPDATE feedback SET admin_reply = ?, status = 'responded' WHERE id = ?",
                (admin_reply, feedback_id)
            )
            conn.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "id": feedback_id,
                "admin_reply": admin_reply
            },
            "meta": {"message": "Response added successfully"}
        })
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}}), 500

@bp.route("/products/bulk-upload", methods=["POST"])
@admin_required
def bulk_upload_products():
    """Bulk upload products from CSV/Excel"""
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "meta": {"error": "No file uploaded"}})
        
        file = request.files['file']
        if not file.filename:
            return jsonify({"success": False, "meta": {"error": "No file selected"}})
        
        # Read file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return jsonify({"success": False, "meta": {"error": "Unsupported file format"}})
        
        # Validate required columns
        required_cols = ['name', 'price']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            return jsonify({"success": False, "meta": {"error": f"Missing columns: {missing_cols}"}})
        
        # Insert products
        count = 0
        with get_conn() as conn:
            cur = conn.cursor()
            for _, row in df.iterrows():
                try:
                    name = str(row['name']).strip()
                    price = float(row['price'])
                    category = str(row.get('category', 'General')).strip()
                    sku = str(row.get('sku', '')).strip() or None
                    description = str(row.get('description', '')).strip() or None
                    
                    if name and price > 0:
                        cur.execute("""
                            INSERT INTO products (name, price, category, sku, description, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (name, price, category, sku, description, datetime.utcnow().isoformat()))
                        count += 1
                except (ValueError, TypeError):
                    continue  # Skip invalid rows
            conn.commit()
        
        return jsonify({
            "success": True,
            "data": {"count": count},
            "meta": {}
        })
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/products/<int:product_id>/delete", methods=["DELETE"])
@admin_required
def delete_product(product_id):
    """Delete a product"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM products WHERE id = ?", (product_id,))
            if cur.rowcount == 0:
                return jsonify({"success": False, "meta": {"error": "Product not found"}})
            conn.commit()
        
        return jsonify({"success": True, "data": {}, "meta": {}})
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/check-expiries", methods=["GET"])
@admin_required
def check_expiries():
    """Check for expired products and generate notifications"""
    try:
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        notifications = []
        
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Check expired products
            expired_products = cur.execute("""
                SELECT id, name, sku, expiry_date, price 
                FROM products 
                WHERE expiry_date IS NOT NULL AND date(expiry_date) < date('now')
            """).fetchall()
            
            # Check products expiring soon (within 7 days)
            expiring_soon = cur.execute("""
                SELECT id, name, sku, expiry_date, price 
                FROM products 
                WHERE expiry_date IS NOT NULL 
                AND date(expiry_date) >= date('now') 
                AND date(expiry_date) <= date('now', '+7 days')
            """).fetchall()
            
            # Generate notifications for expired products
            for product in expired_products:
                expiry_date = datetime.strptime(product[3], '%Y-%m-%d').date()
                days_overdue = (today - expiry_date).days
                
                notification = {
                    "type": "expired",
                    "title": f"EXPIRED: {product[1]}",
                    "message": f"Product {product[1]} (SKU: {product[2] or 'N/A'}) expired {days_overdue} days ago. Consider removing from inventory.",
                    "product_id": product[0],
                    "days_overdue": days_overdue,
                    "created_at": datetime.now().isoformat()
                }
                notifications.append(notification)
                
                # Save notification to database
                cur.execute("""
                    INSERT OR IGNORE INTO notifications (type, title, message, data, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (notification["type"], notification["title"], notification["message"], 
                     str(product[0]), notification["created_at"]))
            
            # Generate notifications for products expiring soon
            for product in expiring_soon:
                expiry_date = datetime.strptime(product[3], '%Y-%m-%d').date()
                days_left = (expiry_date - today).days
                
                notification = {
                    "type": "expiring_soon",
                    "title": f"EXPIRING SOON: {product[1]}",
                    "message": f"Product {product[1]} (SKU: {product[2] or 'N/A'}) expires in {days_left} days. Plan sales or promotions.",
                    "product_id": product[0],
                    "days_left": days_left,
                    "created_at": datetime.now().isoformat()
                }
                notifications.append(notification)
            
            conn.commit()
        
        return jsonify({
            "success": True,
            "data": {
                "notifications": notifications,
                "expired_count": len(expired_products),
                "expiring_soon_count": len(expiring_soon)
            },
            "meta": {"check_date": today.isoformat()}
        })
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/expired-products", methods=["GET"])
@admin_required
def get_expired_products():
    """Get list of expired products"""
    try:
        from datetime import datetime
        
        with get_conn() as conn:
            cur = conn.cursor()
            rows = cur.execute("""
                SELECT id, name, sku, expiry_date, price, category
                FROM products 
                WHERE expiry_date IS NOT NULL AND date(expiry_date) < date('now')
                ORDER BY expiry_date ASC
            """).fetchall()
        
        products = []
        today = datetime.now().date()
        
        for row in rows:
            expiry_date = datetime.strptime(row[3], '%Y-%m-%d').date()
            days_overdue = (today - expiry_date).days
            
            products.append({
                "id": row[0],
                "name": row[1],
                "sku": row[2],
                "expiry_date": row[3],
                "price": row[4],
                "category": row[5],
                "days_overdue": days_overdue
            })
        
        return jsonify({"success": True, "data": products, "meta": {}})
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/expiring-soon", methods=["GET"])
@admin_required
def get_expiring_soon():
    """Get products expiring within 7 days"""
    try:
        from datetime import datetime
        
        with get_conn() as conn:
            cur = conn.cursor()
            rows = cur.execute("""
                SELECT id, name, sku, expiry_date, price, category
                FROM products 
                WHERE expiry_date IS NOT NULL 
                AND date(expiry_date) >= date('now') 
                AND date(expiry_date) <= date('now', '+7 days')
                ORDER BY expiry_date ASC
            """).fetchall()
        
        products = []
        today = datetime.now().date()
        
        for row in rows:
            expiry_date = datetime.strptime(row[3], '%Y-%m-%d').date()
            days_left = (expiry_date - today).days
            
            products.append({
                "id": row[0],
                "name": row[1],
                "sku": row[2],
                "expiry_date": row[3],
                "price": row[4],
                "category": row[5],
                "days_left": days_left
            })
        
        return jsonify({"success": True, "data": products, "meta": {}})
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/expiry-analysis", methods=["GET"])
@admin_required
def expiry_analysis():
    """Perform comprehensive expiry analysis with charts"""
    try:
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Get expired products
            expired = cur.execute("""
                SELECT id, name, sku, expiry_date, price, category
                FROM products 
                WHERE expiry_date IS NOT NULL AND date(expiry_date) < date('now')
            """).fetchall()
            
            # Get expiring soon
            expiring_soon = cur.execute("""
                SELECT id, name, sku, expiry_date, price, category
                FROM products 
                WHERE expiry_date IS NOT NULL 
                AND date(expiry_date) >= date('now') 
                AND date(expiry_date) <= date('now', '+7 days')
            """).fetchall()
            
            # Calculate metrics
            total_expired = len(expired)
            total_expiring_soon = len(expiring_soon)
            estimated_loss = sum(row[4] or 0 for row in expired)
            
            # Calculate average days overdue
            today = datetime.now().date()
            days_overdue_list = []
            for row in expired:
                if row[3]:  # expiry_date exists
                    expiry_date = datetime.strptime(row[3], '%Y-%m-%d').date()
                    days_overdue_list.append((today - expiry_date).days)
            
            avg_days_overdue = sum(days_overdue_list) / len(days_overdue_list) if days_overdue_list else 0
            
            # Generate charts data
            charts = {}
            
            # Loss by category chart
            category_loss = defaultdict(float)
            for row in expired:
                category = row[5] or 'Unknown'
                price = row[4] or 0
                category_loss[category] += price
            
            if category_loss:
                charts["loss"] = {
                    "labels": list(category_loss.keys()),
                    "datasets": [{
                        "data": list(category_loss.values()),
                        "backgroundColor": [
                            "#ef4444", "#f97316", "#eab308", "#22c55e", "#3b82f6",
                            "#8b5cf6", "#ec4899", "#06b6d4"
                        ]
                    }]
                }
            
            # Expiry trends over last 30 days
            trend_data = defaultdict(int)
            for i in range(30):
                date = today - timedelta(days=i)
                trend_data[date.strftime('%m-%d')] = 0
            
            for row in expired:
                if row[3]:
                    expiry_date = datetime.strptime(row[3], '%Y-%m-%d').date()
                    if (today - expiry_date).days <= 30:
                        trend_data[expiry_date.strftime('%m-%d')] += 1
            
            sorted_dates = sorted(trend_data.keys())
            charts["trends"] = {
                "labels": sorted_dates,
                "datasets": [{
                    "label": "Products Expired",
                    "data": [trend_data[date] for date in sorted_dates],
                    "borderColor": "#ef4444",
                    "backgroundColor": "rgba(239, 68, 68, 0.1)",
                    "tension": 0.4
                }]
            }
        
        return jsonify({
            "success": True,
            "data": {
                "total_expired": total_expired,
                "expiring_soon": total_expiring_soon,
                "estimated_loss": estimated_loss,
                "avg_days_overdue": avg_days_overdue,
                "charts": charts
            },
            "meta": {"analysis_date": today.isoformat()}
        })
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/realtime-metrics", methods=["GET"])
@admin_required
def realtime_metrics():
    """Get real-time metrics for dashboard"""
    try:
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Today's revenue
            today_revenue = cur.execute("""
                SELECT COALESCE(SUM(total), 0) FROM orders 
                WHERE date(created_at) = date('now')
            """).fetchone()[0]
            
            # Yesterday's revenue for comparison
            yesterday_revenue = cur.execute("""
                SELECT COALESCE(SUM(total), 0) FROM orders 
                WHERE date(created_at) = date('now', '-1 day')
            """).fetchone()[0]
            
            # Today's orders
            today_orders = cur.execute("""
                SELECT COUNT(*) FROM orders 
                WHERE date(created_at) = date('now')
            """).fetchone()[0]
            
            # Yesterday's orders
            yesterday_orders = cur.execute("""
                SELECT COUNT(*) FROM orders 
                WHERE date(created_at) = date('now', '-1 day')
            """).fetchone()[0]
            
            # Average rating today
            avg_rating = cur.execute("""
                SELECT COALESCE(AVG(CAST(rating AS FLOAT)), 0) FROM feedback 
                WHERE date(created_at) = date('now') AND rating IS NOT NULL
            """).fetchone()[0]
            
            # Feedback count today
            feedback_count = cur.execute("""
                SELECT COUNT(*) FROM feedback 
                WHERE date(created_at) = date('now')
            """).fetchone()[0]
            
            # Active users (users who placed orders in last 24 hours)
            active_users = cur.execute("""
                SELECT COUNT(DISTINCT customer_name) FROM orders 
                WHERE datetime(created_at) >= datetime('now', '-24 hours')
            """).fetchone()[0]
            
            # Calculate changes
            revenue_change = 0
            if yesterday_revenue > 0:
                revenue_change = ((today_revenue - yesterday_revenue) / yesterday_revenue) * 100
            
            orders_change = today_orders - yesterday_orders
        
        return jsonify({
            "success": True,
            "data": {
                "revenue": today_revenue,
                "orders": today_orders,
                "avg_rating": avg_rating,
                "active_users": active_users,
                "revenue_change": revenue_change,
                "orders_change": orders_change,
                "feedback_count": feedback_count
            },
            "meta": {"timestamp": datetime.now().isoformat()}
        })
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/realtime-charts", methods=["GET"])
@admin_required
def realtime_charts():
    """Get chart data for real-time dashboard"""
    try:
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Revenue trend (last 24 hours, hourly)
            revenue_data = defaultdict(float)
            now = datetime.now()
            
            # Initialize last 24 hours
            for i in range(24):
                hour = now - timedelta(hours=i)
                revenue_data[hour.strftime('%H:00')] = 0
            
            # Get actual revenue data
            revenue_rows = cur.execute("""
                SELECT strftime('%H:00', created_at) as hour, SUM(total) as revenue
                FROM orders 
                WHERE datetime(created_at) >= datetime('now', '-24 hours')
                GROUP BY strftime('%H:00', created_at)
            """).fetchall()
            
            for row in revenue_rows:
                revenue_data[row[0]] = row[1]
            
            # Orders trend (last 24 hours, hourly)
            orders_data = defaultdict(int)
            
            # Initialize last 24 hours
            for i in range(24):
                hour = now - timedelta(hours=i)
                orders_data[hour.strftime('%H:00')] = 0
            
            # Get actual orders data
            orders_rows = cur.execute("""
                SELECT strftime('%H:00', created_at) as hour, COUNT(*) as orders
                FROM orders 
                WHERE datetime(created_at) >= datetime('now', '-24 hours')
                GROUP BY strftime('%H:00', created_at)
            """).fetchall()
            
            for row in orders_rows:
                orders_data[row[0]] = row[1]
            
            # Sort hours
            sorted_hours = sorted(revenue_data.keys())
            
            charts = {
                "revenue": {
                    "labels": sorted_hours,
                    "datasets": [{
                        "label": "Revenue ($)",
                        "data": [revenue_data[hour] for hour in sorted_hours],
                        "borderColor": "#3b82f6",
                        "backgroundColor": "rgba(59, 130, 246, 0.1)",
                        "tension": 0.4
                    }]
                },
                "orders": {
                    "labels": sorted_hours,
                    "datasets": [{
                        "label": "Orders",
                        "data": [orders_data[hour] for hour in sorted_hours],
                        "backgroundColor": "#10b981"
                    }]
                }
            }
        
        return jsonify({
            "success": True,
            "data": {"charts": charts},
            "meta": {"timestamp": datetime.now().isoformat()}
        })
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/top-products", methods=["GET"])
@admin_required
def top_products():
    """Get top performing products"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Get top products by revenue (from order items)
            rows = cur.execute("""
                SELECT p.id, p.name, p.sku, 
                       SUM(oi.qty * oi.price) as revenue,
                       SUM(oi.qty) as sales
                FROM products p
                JOIN order_items oi ON p.id = oi.product_id
                JOIN orders o ON oi.order_id = o.id
                WHERE date(o.created_at) >= date('now', '-7 days')
                GROUP BY p.id, p.name, p.sku
                ORDER BY revenue DESC
                LIMIT 5
            """).fetchall()
            
            products = []
            for row in rows:
                products.append({
                    "id": row[0],
                    "name": row[1],
                    "sku": row[2],
                    "revenue": row[3],
                    "sales": row[4]
                })
        
        return jsonify({"success": True, "data": products, "meta": {}})
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})

@bp.route("/recent-activity", methods=["GET"])
@admin_required
def recent_activity():
    """Get recent system activity"""
    try:
        from datetime import datetime
        
        activities = []
        
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Recent orders
            orders = cur.execute("""
                SELECT created_at, customer_name, total
                FROM orders 
                ORDER BY created_at DESC 
                LIMIT 5
            """).fetchall()
            
            for order in orders:
                activities.append({
                    "type": "order",
                    "description": f"New order from {order[1]}",
                    "value": f"${order[2]:.2f}",
                    "status": "completed",
                    "created_at": order[0]
                })
            
            # Recent feedback
            feedback = cur.execute("""
                SELECT created_at, rating, text
                FROM feedback 
                ORDER BY created_at DESC 
                LIMIT 3
            """).fetchall()
            
            for fb in feedback:
                activities.append({
                    "type": "feedback",
                    "description": f"New {fb[1]}-star feedback received",
                    "value": f"{fb[1]}⭐",
                    "status": "pending" if not fb[2] else "completed",
                    "created_at": fb[0]
                })
            
            # Recent products
            products = cur.execute("""
                SELECT created_at, name, price
                FROM products 
                WHERE created_at IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 2
            """).fetchall()
            
            for product in products:
                activities.append({
                    "type": "product",
                    "description": f"Product '{product[1]}' added",
                    "value": f"${product[2]:.2f}",
                    "status": "completed",
                    "created_at": product[0]
                })
        
        # Sort all activities by timestamp
        activities.sort(key=lambda x: x["created_at"], reverse=True)
        
        return jsonify({
            "success": True,
            "data": activities[:10],  # Return top 10 most recent
            "meta": {}
        })
        
    except Exception as e:
        return jsonify({"success": False, "meta": {"error": str(e)}})


@bp.route("/store-performance", methods=["GET"])
@admin_required
def store_performance():
    """Get performance data for all stores"""
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Get all stores
            stores = cur.execute("""
                SELECT id, name, location, manager, created_at
                FROM stores
                ORDER BY name
            """).fetchall()
            
            store_data = []
            
            for store in stores:
                store_id, name, location, manager, created_at = store
                
                # Get store metrics (revenue from sales_data table if exists)
                try:
                    revenue = cur.execute("""
                        SELECT COALESCE(SUM(revenue), 0) as total_revenue
                        FROM sales_data
                        WHERE store_id = ?
                    """, (store_id,)).fetchone()[0]
                except:
                    revenue = 0
                
                # Get order count (if orders table has store_id)
                try:
                    orders = cur.execute("""
                        SELECT COUNT(*) as order_count
                        FROM orders
                        WHERE store_id = ?
                    """, (store_id,)).fetchone()[0]
                except:
                    orders = 0
                
                # Calculate status (active if has recent activity)
                status = "active" if orders > 0 or revenue > 0 else "idle"
                
                store_data.append({
                    "id": store_id,
                    "name": name,
                    "location": location,
                    "manager": manager,
                    "revenue": float(revenue),
                    "orders": orders,
                    "status": status,
                    "created_at": created_at
                })
            
            return jsonify({
                "success": True,
                "data": store_data,
                "meta": {
                    "total_stores": len(store_data)
                }
            })
        
    except Exception as e:
        print(f"[ERROR] Store performance: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "meta": {"error": str(e)}})
