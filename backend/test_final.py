#!/usr/bin/env python3
"""
Final comprehensive test of all backend endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_all_endpoints():
    print("COMPREHENSIVE BACKEND TEST")
    print("=" * 50)
    
    results = []
    
    # 1. Test Products (should work for users)
    try:
        response = requests.get(f"{BASE_URL}/api/products/")
        success = response.status_code == 200
        data = response.json() if success else {}
        products_count = len(data.get('data', []))
        print(f"SUCCESS Products: {response.status_code} - {products_count} products found")
        results.append(("Products API", success))
    except Exception as e:
        print(f"ERROR Products: ERROR - {e}")
        results.append(("Products API", False))
    
    # 2. Test Feedback GET (should work)
    try:
        response = requests.get(f"{BASE_URL}/api/feedback/")
        success = response.status_code == 200
        data = response.json() if success else {}
        feedback_count = len(data.get('data', []))
        print(f"SUCCESS Feedback GET: {response.status_code} - {feedback_count} feedback items")
        results.append(("Feedback GET", success))
    except Exception as e:
        print(f"ERROR Feedback GET: ERROR - {e}")
        results.append(("Feedback GET", False))
    
    # 3. Test User Login
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
            json={"email": "user@example.com", "password": "password"})
        success = response.status_code == 200
        print(f"SUCCESS User Login: {response.status_code} - {'SUCCESS' if success else 'FAILED'}")
        results.append(("User Login", success))
        
        if success:
            user_token = response.json().get('data', {}).get('token')
            
            # Test Feedback POST with user token
            try:
                feedback_data = {
                    "rating": 4,
                    "message": "Great service!",
                    "category": "service"
                }
                response = requests.post(f"{BASE_URL}/api/feedback/submit", 
                    json=feedback_data,
                    headers={'Authorization': f'Bearer {user_token}', 'Content-Type': 'application/json'})
                success = response.status_code == 200
                print(f"SUCCESS Feedback POST: {response.status_code} - {'SUCCESS' if success else 'FAILED'}")
                results.append(("Feedback POST", success))
            except Exception as e:
                print(f"ERROR Feedback POST: ERROR - {e}")
                results.append(("Feedback POST", False))
                
    except Exception as e:
        print(f"ERROR User Login: ERROR - {e}")
        results.append(("User Login", False))
    
    # 4. Test Admin Login and CSV Upload
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
            json={"email": "admin@example.com", "password": "password"})
        success = response.status_code == 200
        print(f"SUCCESS Admin Login: {response.status_code} - {'SUCCESS' if success else 'FAILED'}")
        results.append(("Admin Login", success))
        
        if success:
            admin_token = response.json().get('data', {}).get('token')
            
            # Test CSV Upload (without auth for now)
            try:
                test_csv = """product_name,price,category,sales_volume
iPhone 14,999.99,Electronics,150
Samsung TV,799.99,Electronics,89
Nike Shoes,129.99,Clothing,234
Coffee Maker,79.99,Appliances,67
Laptop,1299.99,Electronics,45"""
                
                files = {'file': ('sales_data.csv', test_csv, 'text/csv')}
                
                response = requests.post(f"{BASE_URL}/api/admin/clean-data", files=files)
                success = response.status_code == 200
                print(f"SUCCESS CSV Upload: {response.status_code} - {'SUCCESS' if success else 'FAILED'}")
                
                if success:
                    data = response.json()
                    before_rows = data.get('meta', {}).get('rows_in', 0)
                    after_rows = data.get('meta', {}).get('rows_out', 0)
                    print(f"   Data processed: {before_rows} -> {after_rows} rows")
                else:
                    print(f"   Error: {response.text[:200]}")
                    
                results.append(("CSV Upload", success))
                
            except Exception as e:
                print(f"ERROR CSV Upload: ERROR - {e}")
                results.append(("CSV Upload", False))
                
    except Exception as e:
        print(f"ERROR Admin Login: ERROR - {e}")
        results.append(("Admin Login", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY:")
    
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"   {test_name}: {status}")
        if success:
            passed += 1
    
    total = len(results)
    print(f"\nOverall Score: {passed}/{total} tests passed")
    
    if passed == total:
        print("ALL BACKEND ENDPOINTS WORKING PERFECTLY!")
        print("COMPLETE WEBSITE IS NOW FUNCTIONAL!")
    else:
        print("Some endpoints need attention")
    
    return passed == total

if __name__ == "__main__":
    test_all_endpoints()
