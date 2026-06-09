#!/usr/bin/env python3
"""
Test the fixed admin upload page
"""
import requests

BASE_URL = "http://localhost:8000"

def test_admin_upload_fixed():
    """Test the fixed admin upload functionality"""
    print("TESTING FIXED ADMIN UPLOAD")
    print("=" * 40)
    
    # Create test CSV data
    test_csv = """product_name,price,category,sales_volume,profit_margin
iPhone 14,999.99,Electronics,150,0.25
Samsung TV,799.99,Electronics,89,0.20
Nike Shoes,129.99,Clothing,234,0.35
Coffee Maker,79.99,Appliances,67,0.30
Laptop,1299.99,Electronics,45,0.15"""
    
    try:
        files = {'file': ('test_sales.csv', test_csv, 'text/csv')}
        
        response = requests.post(f"{BASE_URL}/api/admin/clean-data", files=files)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("Response structure:")
            print(f"  success: {data.get('success')}")
            print(f"  meta keys: {list(data.get('meta', {}).keys())}")
            print(f"  data keys: {list(data.get('data', {}).keys())}")
            
            if data.get('success'):
                print("\nSUCCESS: Admin upload working!")
                
                # Check response structure
                meta = data.get('meta', {})
                data_section = data.get('data', {})
                
                print(f"\nMeta info:")
                print(f"  rows_in: {meta.get('rows_in')}")
                print(f"  rows_out: {meta.get('rows_out')}")
                print(f"  quality_improved: {meta.get('quality_improved')}")
                
                print(f"\nData structure:")
                if 'before' in data_section:
                    print("  - Has 'before' section")
                if 'after' in data_section:
                    print("  - Has 'after' section")
                if 'improvement' in data_section:
                    print("  - Has 'improvement' section")
                
                return True
            else:
                print(f"ERROR: {data.get('meta', {}).get('error', 'Unknown error')}")
        else:
            print(f"ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text[:300]}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    return False

if __name__ == "__main__":
    success = test_admin_upload_fixed()
    if success:
        print("\n✅ ADMIN UPLOAD IS NOW WORKING!")
        print("✅ JavaScript errors should be fixed!")
    else:
        print("\n❌ Still has issues")
