#!/usr/bin/env python3
"""
Test script to verify products API is working
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_products():
    print("Testing Products API...")
    
    # Test GET products
    try:
        response = requests.get(f"{BASE_URL}/api/products/")
        print(f"GET /api/products/ - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Products loaded: {len(data.get('data', []))} items")
        else:
            print(f"ERROR: {response.text}")
    except Exception as e:
        print(f"ERROR: Connection error: {e}")
    
    # Test POST product
    try:
        test_product = {
            "name": "Test Product",
            "price": 29.99,
            "category": "Electronics",
            "sku": "TEST-001",
            "description": "Test product for API verification"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/products/",
            json=test_product,
            headers={"Content-Type": "application/json"}
        )
        print(f"POST /api/products/ - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Product created: ID {data.get('data', {}).get('id')}")
        else:
            print(f"ERROR: {response.text}")
    except Exception as e:
        print(f"ERROR: Connection error: {e}")

def test_feedback():
    print("\nTesting Feedback API...")
    
    # Test GET feedback
    try:
        response = requests.get(f"{BASE_URL}/api/feedback/")
        print(f"GET /api/feedback/ - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Feedback loaded: {len(data.get('data', []))} items")
        else:
            print(f"ERROR: {response.text}")
    except Exception as e:
        print(f"ERROR: Connection error: {e}")
    
    # Test POST feedback
    try:
        test_feedback = {
            "rating": 5,
            "message": "Test feedback message",
            "category": "product"
        }
        
        response = requests.post(
            f"{BASE_URL}/api/feedback/submit",
            json=test_feedback,
            headers={"Content-Type": "application/json"}
        )
        print(f"POST /api/feedback/submit - Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"SUCCESS: Feedback submitted: ID {data.get('data', {}).get('id')}")
        else:
            print(f"ERROR: {response.text}")
    except Exception as e:
        print(f"ERROR: Connection error: {e}")

if __name__ == "__main__":
    test_products()
    test_feedback()
    print("\nAPI Testing Complete!")
