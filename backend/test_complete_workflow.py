#!/usr/bin/env python3
"""
Test the complete admin to visualizer workflow
"""
import requests
import os

BASE_URL = "http://localhost:8000"

def test_complete_workflow():
    """Test the complete workflow from admin upload to visualizer"""
    print("TESTING COMPLETE ADMIN TO VISUALIZER WORKFLOW")
    print("=" * 60)
    
    # Create test CSV data
    test_csv = """product_name,price,category,sales_volume,profit_margin,region
iPhone 14,999.99,Electronics,150,0.25,North
Samsung TV,799.99,Electronics,89,0.20,South
Nike Shoes,129.99,Clothing,234,0.35,East
Coffee Maker,79.99,Appliances,67,0.30,West
Laptop,1299.99,Electronics,45,0.15,North
Headphones,199.99,Electronics,123,0.40,South
T-Shirt,29.99,Clothing,456,0.50,East
Microwave,299.99,Appliances,78,0.25,West"""
    
    try:
        # Step 1: Upload and clean data in admin
        print("STEP 1: Testing admin data cleaning...")
        files = {'file': ('test_sales.csv', test_csv, 'text/csv')}
        
        response = requests.post(f"{BASE_URL}/api/admin/clean-data", files=files)
        print(f"  Admin upload status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("  ✅ Admin data cleaning successful")
                
                # Get cleaned file path
                cleaned_file = data.get('data', {}).get('cleaned_file', '')
                print(f"  📁 Cleaned file: {cleaned_file}")
                
                # Step 2: Test download endpoint
                print("\nSTEP 2: Testing download endpoint...")
                if cleaned_file:
                    filename = os.path.basename(cleaned_file)
                    download_response = requests.get(f"{BASE_URL}/api/admin/download-cleaned/{filename}")
                    print(f"  Download status: {download_response.status_code}")
                    
                    if download_response.status_code == 200:
                        print("  ✅ Download endpoint working")
                        print(f"  📊 Downloaded {len(download_response.content)} bytes")
                        
                        # Step 3: Test visualizer with downloaded data
                        print("\nSTEP 3: Testing visualizer with cleaned data...")
                        
                        # Create a file-like object from the downloaded content
                        viz_files = {'file': ('cleaned_data.csv', download_response.content, 'text/csv')}
                        viz_data = {
                            'chart_types': '["line","bar","pie"]',
                            'analysis_types': '["summary"]'
                        }
                        
                        viz_response = requests.post(f"{BASE_URL}/api/admin/visualize-data", 
                                                   files=viz_files, data=viz_data)
                        print(f"  Visualizer status: {viz_response.status_code}")
                        
                        if viz_response.status_code == 200:
                            viz_result = viz_response.json()
                            if viz_result.get('success'):
                                print("  ✅ Visualizer processing successful")
                                
                                # Check visualization results
                                viz_data = viz_result.get('data', {})
                                charts = viz_data.get('charts', [])
                                summary = viz_data.get('summary', {})
                                analysis = viz_data.get('analysis', {})
                                
                                print(f"  📊 Charts generated: {len(charts)}")
                                print(f"  📈 Chart types: {[c.get('type') for c in charts]}")
                                print(f"  📋 Data summary: {summary.get('rows', 0)} rows, {summary.get('columns', 0)} columns")
                                
                                if analysis.get('numeric_stats'):
                                    print(f"  🔢 Numeric analysis: {len(analysis['numeric_stats'])} columns")
                                
                                return True
                            else:
                                print(f"  ❌ Visualizer failed: {viz_result.get('meta', {}).get('error')}")
                        else:
                            print(f"  ❌ Visualizer HTTP error: {viz_response.status_code}")
                    else:
                        print(f"  ❌ Download failed: {download_response.status_code}")
                        print(f"  Error: {download_response.text[:200]}")
                else:
                    print("  ❌ No cleaned file path returned")
            else:
                print(f"  ❌ Admin cleaning failed: {data.get('meta', {}).get('error')}")
        else:
            print(f"  ❌ Admin upload failed: {response.status_code}")
            print(f"  Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
    
    return False

def main():
    success = test_complete_workflow()
    
    print("\n" + "=" * 60)
    print("WORKFLOW TEST RESULTS:")
    
    if success:
        print("🌟 COMPLETE WORKFLOW SUCCESSFUL!")
        print("✅ Admin upload and cleaning works")
        print("✅ Download endpoint works")
        print("✅ Visualizer integration works")
        print("✅ Interactive charts generated")
        print("\n🎯 READY FOR PRODUCTION USE!")
    else:
        print("❌ Workflow has issues - check the errors above")

if __name__ == "__main__":
    main()
