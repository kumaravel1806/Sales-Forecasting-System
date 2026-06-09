#!/usr/bin/env python3
"""
Test login functionality for both admin and regular users
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_login(email, password, expected_role):
    print(f"\nTesting login: {email}")
    
    try:
        response = requests.post(f"{BASE_URL}/api/auth/login", 
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                user = data.get('data', {}).get('user', {})
                print(f"SUCCESS: Logged in as {user.get('username')} (role: {user.get('role')})")
                
                if user.get('role') == expected_role:
                    print(f"CORRECT: Role matches expected ({expected_role})")
                else:
                    print(f"ERROR: Role mismatch. Expected {expected_role}, got {user.get('role')}")
                    
                return True
            else:
                print(f"ERROR: {data.get('meta', {}).get('error', 'Unknown error')}")
        else:
            print(f"ERROR: HTTP {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"ERROR: Connection failed - {e}")
    
    return False

def main():
    print("Testing Login System...")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("admin@example.com", "password", "admin"),
        ("user@example.com", "password", "user"),
        ("john@example.com", "password123", "user"),
        ("jane@example.com", "password123", "user"),
        ("invalid@example.com", "wrongpass", None)  # Should fail
    ]
    
    success_count = 0
    
    for email, password, expected_role in test_cases:
        if expected_role is None:
            # This should fail
            print(f"\nTesting invalid login: {email}")
            try:
                response = requests.post(f"{BASE_URL}/api/auth/login", 
                    json={"email": email, "password": password},
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code != 200:
                    print("SUCCESS: Invalid login correctly rejected")
                    success_count += 1
                else:
                    print("ERROR: Invalid login was accepted")
            except Exception as e:
                print(f"ERROR: {e}")
        else:
            if test_login(email, password, expected_role):
                success_count += 1
    
    print("\n" + "=" * 50)
    print(f"Test Results: {success_count}/{len(test_cases)} passed")
    
    if success_count == len(test_cases):
        print("ALL TESTS PASSED - Login system working correctly!")
    else:
        print("SOME TESTS FAILED - Check the issues above")

if __name__ == "__main__":
    main()
