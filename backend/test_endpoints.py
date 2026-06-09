#!/usr/bin/env python3
"""
Test all backend endpoints to identify issues
"""
import requests
import json
import os

BASE_URL = "http://localhost:8000"

def get_admin_token():
    """Get admin token for authenticated requests"""
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
            json={"email": "admin@example.com", "password": "password"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('token')
    except Exception as e:
        print(f"Failed to get admin token: {e}")
    return None

def get_user_token():
    """Get user token for authenticated requests"""
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
            json={"email": "user@example.com", "password": "password"},
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            data = response.json()
            return data.get('data', {}).get('token')
    except Exception as e:
        print(f"Failed to get user token: {e}")
    return None

def test_csv_upload():
    """Test CSV upload for data cleaning"""
    print("\n=== TESTING CSV UPLOAD ===")
    
    admin_token = get_admin_token()
    if not admin_token:
        print("ERROR: Could not get admin token")
        return False
    
    # Create a test CSV file
    test_csv_content = """product_name,price,category,sales
iPhone 14,999.99,Electronics,150
Samsung TV,799.99,Electronics,89
Nike Shoes,129.99,Clothing,234
Coffee Maker,79.99,Appliances,67"""
    
    csv_file_path = "test_data.csv"
    with open(csv_file_path, 'w') as f:
        f.write(test_csv_content)
    
    try:
        with open(csv_file_path, 'rb') as f:
            files = {'file': ('test_data.csv', f, 'text/csv')}
            headers = {'Authorization': f'Bearer {admin_token}'}
            
            response = requests.post(f"{BASE_URL}/api/admin/clean-data", 
                files=files, headers=headers)
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:500]}...")
            
            if response.status_code == 200:
                print("SUCCESS: CSV upload working")
                return True
            else:
                print(f"ERROR: CSV upload failed - {response.status_code}")
                return False
                
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        if os.path.exists(csv_file_path):
            os.remove(csv_file_path)

def test_feedback_endpoint():
    """Test feedback endpoints"""
    print("\n=== TESTING FEEDBACK ===")
    
    user_token = get_user_token()
    admin_token = get_admin_token()
    
    # Test feedback submission
    try:
        headers = {'Content-Type': 'application/json'}
        if user_token:
            headers['Authorization'] = f'Bearer {user_token}'
            
        feedback_data = {
            "rating": 5,
            "message": "Great product!",
            "category": "product",
            "store_id": "1"
        }
        
        response = requests.post(f"{BASE_URL}/api/feedback/submit", 
            json=feedback_data, headers=headers)
        
        print(f"Feedback Submit Status: {response.status_code}")
        print(f"Submit Response: {response.text}")
        
    except Exception as e:
        print(f"Feedback submit error: {e}")
    
    # Test feedback retrieval
    try:
        headers = {}
        if admin_token:
            headers['Authorization'] = f'Bearer {admin_token}'
            
        response = requests.get(f"{BASE_URL}/api/feedback/", headers=headers)
        print(f"Feedback Get Status: {response.status_code}")
        print(f"Get Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Feedback endpoints working")
            return True
        else:
            print("ERROR: Feedback endpoints failed")
            return False
            
    except Exception as e:
        print(f"Feedback get error: {e}")
        return False

def test_products_endpoint():
    """Test products endpoints"""
    print("\n=== TESTING PRODUCTS ===")
    
    try:
        # Test getting products (should work without auth for users)
        response = requests.get(f"{BASE_URL}/api/products/")
        print(f"Products Get Status: {response.status_code}")
        print(f"Products Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                products = data.get('data', [])
                print(f"SUCCESS: Found {len(products)} products")
                return True
            else:
                print("ERROR: Products response not successful")
                return False
        else:
            print(f"ERROR: Products endpoint failed - {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Products error: {e}")
        return False

def main():
    print("TESTING ALL BACKEND ENDPOINTS...")
    print("=" * 50)
    
    results = []
    
    # Test CSV upload
    results.append(("CSV Upload", test_csv_upload()))
    
    # Test feedback
    results.append(("Feedback", test_feedback_endpoint()))
    
    # Test products
    results.append(("Products", test_products_endpoint()))
    
    print("\n" + "=" * 50)
    print("TEST RESULTS:")
    
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"  {test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("ALL BACKEND ENDPOINTS WORKING!")
    else:
        print("SOME ENDPOINTS NEED FIXING!")

if __name__ == "__main__":
    main()
