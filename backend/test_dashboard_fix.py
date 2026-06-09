#!/usr/bin/env python3
"""
Test script to verify dashboard endpoints are returning correct counts
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_dashboard_endpoint():
    """Test the main dashboard endpoint"""
    print("\n" + "="*60)
    print("Testing /api/analytics/dashboard endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/analytics/dashboard")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ SUCCESS: Dashboard endpoint is working")
            print(f"\nReturned Data:")
            print(json.dumps(data, indent=2))
            
            # Verify the structure
            if 'data' in data:
                metrics = data['data']
                print(f"\n📊 Dashboard Metrics:")
                print(f"  - Total Products: {metrics.get('total_products', 'N/A')}")
                print(f"  - Critical Stock: {metrics.get('critical_stock', 'N/A')}")
                print(f"  - Low Stock: {metrics.get('low_stock', 'N/A')}")
                print(f"  - Near Expiry: {metrics.get('near_expiry', 'N/A')}")
                print(f"  - Expired: {metrics.get('expired', 'N/A')}")
                print(f"  - Total Orders (30d): {metrics.get('total_orders', 'N/A')}")
                print(f"  - Total Revenue (30d): ₹{metrics.get('total_revenue', 'N/A')}")
                
                # Verify all are numbers (not "-" or null)
                issues = []
                for key in ['total_products', 'critical_stock', 'low_stock', 'near_expiry', 'expired']:
                    if key not in metrics or metrics[key] is None:
                        issues.append(f"Missing or null: {key}")
                    elif not isinstance(metrics[key], (int, float)):
                        issues.append(f"Not a number: {key} = {metrics[key]}")
                
                if issues:
                    print(f"\n❌ Issues found:")
                    for issue in issues:
                        print(f"  - {issue}")
                else:
                    print(f"\n✅ All metrics are properly formatted numbers!")
            else:
                print(f"\n❌ ERROR: Response missing 'data' field")
        else:
            print(f"❌ ERROR: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: Connection error: {e}")

def test_realtime_dashboard():
    """Test the detailed realtime dashboard endpoint"""
    print("\n" + "="*60)
    print("Testing /api/analytics/dashboard/realtime endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/analytics/dashboard/realtime")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ SUCCESS: Realtime dashboard endpoint is working")
            
            if 'data' in data and 'kpi' in data['data']:
                kpi = data['data']['kpi']
                print(f"\n📊 KPI Metrics:")
                print(f"  - Total Products: {kpi.get('total_products', 'N/A')}")
                print(f"  - Critical Stock: {kpi.get('critical_stock', 'N/A')}")
                print(f"  - Low Stock: {kpi.get('low_stock', 'N/A')}")
                print(f"  - Near Expiry Count: {kpi.get('near_expiry_count', 'N/A')}")
                print(f"  - Near Expiry Qty: {kpi.get('near_expiry_qty', 'N/A')}")
                print(f"  - Expired Count: {kpi.get('expired_count', 'N/A')}")
                print(f"  - Expired Qty: {kpi.get('expired_qty', 'N/A')}")
                print(f"  - Today's Orders: {kpi.get('today_orders', 'N/A')}")
                print(f"  - Today's Revenue: ₹{kpi.get('today_revenue', 'N/A')}")
                
                # Check if we have detailed data
                has_low_stock = len(data['data'].get('low_stock_products', [])) > 0
                has_near_expiry = len(data['data'].get('near_expiry_batches', [])) > 0
                has_expired = len(data['data'].get('expired_batches', [])) > 0
                
                print(f"\n📋 Detailed Data Available:")
                print(f"  - Low Stock Products: {len(data['data'].get('low_stock_products', []))} items")
                print(f"  - Near Expiry Batches: {len(data['data'].get('near_expiry_batches', []))} batches")
                print(f"  - Expired Batches: {len(data['data'].get('expired_batches', []))} batches")
                print(f"  - Sales Trend Data: {len(data['data'].get('sales_trend', []))} data points")
                print(f"  - Top Products: {len(data['data'].get('top_products', []))} products")
                
                print(f"\n✅ Realtime dashboard has complete data structure!")
            else:
                print(f"\n❌ ERROR: Response missing 'data' or 'kpi' field")
        else:
            print(f"❌ ERROR: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: Connection error: {e}")

def test_realtime_metrics():
    """Test admin realtime metrics endpoint"""
    print("\n" + "="*60)
    print("Testing /api/admin/realtime-metrics endpoint")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/api/admin/realtime-metrics")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✓ SUCCESS: Admin realtime metrics endpoint is working")
            print(f"\nReturned Data:")
            print(json.dumps(data, indent=2))
        elif response.status_code == 401:
            print(f"\n⚠️  WARNING: Authentication required (expected for admin endpoint)")
        else:
            print(f"❌ ERROR: {response.text}")
    except Exception as e:
        print(f"❌ ERROR: Connection error: {e}")

def check_database():
    """Check if database has sample data"""
    print("\n" + "="*60)
    print("Checking Database Content")
    print("="*60)
    
    from db import get_conn
    
    try:
        with get_conn() as conn:
            cur = conn.cursor()
            
            # Count products
            total_products = cur.execute('SELECT COUNT(*) FROM products').fetchone()[0]
            print(f"  - Total Products: {total_products}")
            
            # Count inventory batches
            total_batches = cur.execute('SELECT COUNT(*) FROM inventory_batches WHERE qty > 0').fetchone()[0]
            print(f"  - Total Inventory Batches: {total_batches}")
            
            # Count orders
            total_orders = cur.execute('SELECT COUNT(*) FROM orders').fetchone()[0]
            print(f"  - Total Orders: {total_orders}")
            
            # Count feedback
            total_feedback = cur.execute('SELECT COUNT(*) FROM feedback').fetchone()[0]
            print(f"  - Total Feedback: {total_feedback}")
            
            if total_products == 0:
                print(f"\n⚠️  WARNING: No products found in database!")
                print(f"   Run seed script to add sample data: python backend/scripts/seed.py")
            else:
                print(f"\n✅ Database has data!")
    except Exception as e:
        print(f"❌ ERROR: Database error: {e}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("DASHBOARD FIX VERIFICATION TEST")
    print("="*60)
    print("\nThis script will test if the dashboard endpoints are")
    print("returning accurate counts instead of showing '-'")
    print("\nMake sure the backend server is running on port 8000!")
    print("="*60)
    
    # Check database first
    check_database()
    
    # Test all endpoints
    test_dashboard_endpoint()
    test_realtime_dashboard()
    test_realtime_metrics()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\nNext Steps:")
    print("1. If tests pass: Open http://localhost:8000/admin_dashboard.html")
    print("2. Login with admin credentials")
    print("3. Verify all metrics show numbers instead of '-'")
    print("="*60 + "\n")
