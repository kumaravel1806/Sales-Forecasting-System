#!/usr/bin/env python3
"""
Test CSV upload functionality for both admin page and data visualizer
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_admin_csv_upload():
    """Test CSV upload on admin page"""
    print("TESTING ADMIN PAGE CSV UPLOAD")
    print("-" * 40)
    
    # Create test CSV data
    test_csv = """product_name,price,category,sales_volume,profit_margin
iPhone 14,999.99,Electronics,150,0.25
Samsung TV,799.99,Electronics,89,0.20
Nike Shoes,129.99,Clothing,234,0.35
Coffee Maker,79.99,Appliances,67,0.30
Laptop,1299.99,Electronics,45,0.15
Headphones,199.99,Electronics,123,0.40
T-Shirt,29.99,Clothing,456,0.50
Microwave,299.99,Appliances,78,0.25"""
    
    try:
        files = {'file': ('sales_data.csv', test_csv, 'text/csv')}
        
        response = requests.post(f"{BASE_URL}/api/admin/clean-data", files=files)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("SUCCESS: Admin CSV upload working!")
                print(f"  - Processed: {data.get('meta', {}).get('rows_in', 0)} -> {data.get('meta', {}).get('rows_out', 0)} rows")
                print(f"  - Quality improved: {data.get('meta', {}).get('quality_improved', False)}")
                return True
            else:
                print(f"ERROR: {data.get('meta', {}).get('error', 'Unknown error')}")
        else:
            print(f"ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    return False

def test_visualizer_csv_upload():
    """Test CSV upload on data visualizer page"""
    print("\nTESTING DATA VISUALIZER CSV UPLOAD")
    print("-" * 40)
    
    # Create test CSV data for visualization
    test_csv = """month,revenue,customers,orders,satisfaction_rating
January,45000,1200,890,4.2
February,52000,1350,1020,4.3
March,48000,1280,950,4.1
April,55000,1400,1100,4.4
May,62000,1550,1250,4.5
June,58000,1480,1180,4.3
July,67000,1650,1350,4.6
August,71000,1720,1420,4.7
September,64000,1580,1280,4.4
October,69000,1680,1380,4.5
November,75000,1800,1500,4.8
December,82000,1950,1650,4.9"""
    
    try:
        files = {'file': ('monthly_data.csv', test_csv, 'text/csv')}
        form_data = {
            'chart_types': '["line","bar","pie"]',
            'analysis_types': '["summary"]'
        }
        
        response = requests.post(f"{BASE_URL}/api/admin/visualize-data", 
                               files=files, data=form_data)
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("SUCCESS: Data visualizer CSV upload working!")
                summary = data.get('data', {}).get('summary', {})
                charts = data.get('data', {}).get('charts', [])
                analysis = data.get('data', {}).get('analysis', {})
                
                print(f"  - File processed: {summary.get('file_name', 'Unknown')}")
                print(f"  - Rows: {summary.get('rows', 0)}, Columns: {summary.get('columns', 0)}")
                print(f"  - Charts generated: {len(charts)}")
                print(f"  - Analysis included: {'Yes' if analysis else 'No'}")
                
                # Show chart types generated
                chart_types = [chart.get('type') for chart in charts]
                print(f"  - Chart types: {', '.join(chart_types)}")
                
                return True
            else:
                print(f"ERROR: {data.get('meta', {}).get('error', 'Unknown error')}")
        else:
            print(f"ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    return False

def main():
    print("CSV UPLOAD TESTING FOR BOTH PAGES")
    print("=" * 50)
    
    # Test both pages
    admin_success = test_admin_csv_upload()
    visualizer_success = test_visualizer_csv_upload()
    
    print("\n" + "=" * 50)
    print("FINAL RESULTS:")
    print(f"  Admin Page CSV Upload: {'PASS' if admin_success else 'FAIL'}")
    print(f"  Visualizer CSV Upload: {'PASS' if visualizer_success else 'FAIL'}")
    
    if admin_success and visualizer_success:
        print("\nSUCCESS: Both CSV upload pages are working perfectly!")
        print("Users can now upload CSV files without any errors!")
    else:
        print("\nSome issues remain - check the errors above")
    
    return admin_success and visualizer_success

if __name__ == "__main__":
    main()
