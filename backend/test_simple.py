#!/usr/bin/env python3
"""
Simple test for backend endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_basic_endpoints():
    """Test basic endpoints without authentication"""
    print("TESTING BASIC ENDPOINTS...")
    print("=" * 40)
    
    # Test products endpoint
    try:
        response = requests.get(f"{BASE_URL}/api/products/")
        print(f"Products: {response.status_code} - {len(response.json().get('data', []))} products")
    except Exception as e:
        print(f"Products error: {e}")
    
    # Test feedback GET
    try:
        response = requests.get(f"{BASE_URL}/api/feedback/")
        print(f"Feedback: {response.status_code} - {len(response.json().get('data', []))} feedback items")
    except Exception as e:
        print(f"Feedback error: {e}")
    
    # Test auth login
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
            json={"email": "admin@example.com", "password": "password"})
        print(f"Admin Login: {response.status_code} - {'SUCCESS' if response.status_code == 200 else 'FAILED'}")
        
        if response.status_code == 200:
            token = response.json().get('data', {}).get('token')
            print(f"Token received: {'YES' if token else 'NO'}")
            
            # Test authenticated endpoint
            if token:
                headers = {'Authorization': f'Bearer {token}'}
                
                # Test CSV upload with proper file
                test_csv = "name,price,category\nTest Product,29.99,Electronics\nAnother Product,19.99,Home"
                files = {'file': ('test.csv', test_csv, 'text/csv')}
                
                response = requests.post(f"{BASE_URL}/api/admin/clean-data", 
                    files=files, headers=headers)
                print(f"CSV Upload: {response.status_code} - {'SUCCESS' if response.status_code == 200 else 'FAILED'}")
                
                if response.status_code != 200:
                    print(f"Error: {response.text[:200]}")
        
    except Exception as e:
        print(f"Auth error: {e}")

if __name__ == "__main__":
    test_basic_endpoints()
