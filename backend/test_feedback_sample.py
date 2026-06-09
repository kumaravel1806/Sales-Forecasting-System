#!/usr/bin/env python3
"""
Add sample feedback data for testing
"""

import requests
import json

def add_sample_feedback():
    """Add sample feedback entries"""
    base_url = "http://localhost:8000"
    
    # Sample feedback data
    sample_feedback = [
        {
            "rating": 5,
            "message": "Excellent service! The staff was very helpful and the products are of great quality.",
            "category": "service",
            "store_id": "1"
        },
        {
            "rating": 4,
            "message": "Good experience overall. The store is well organized and prices are reasonable.",
            "category": "general",
            "store_id": "1"
        },
        {
            "rating": 3,
            "message": "Average experience. Some products were out of stock but the staff was helpful.",
            "category": "inventory",
            "store_id": "1"
        },
        {
            "rating": 5,
            "message": "Amazing customer service! They went above and beyond to help me find what I needed.",
            "category": "service",
            "store_id": "2"
        },
        {
            "rating": 2,
            "message": "Long waiting times and some products were expired. Needs improvement.",
            "category": "quality",
            "store_id": "2"
        }
    ]
    
    print("Adding sample feedback data...")
    
    for i, feedback in enumerate(sample_feedback, 1):
        try:
            response = requests.post(f"{base_url}/api/feedback/submit", json=feedback)
            if response.status_code == 200:
                result = response.json()
                print(f"[SUCCESS] Feedback {i} added successfully")
            else:
                print(f"[FAILED] Failed to add feedback {i}: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Error adding feedback {i}: {e}")
    
    print("\nSample feedback data added!")
    print("Now you can test the feedback management page at: http://localhost:8000/feedback_management.html")

if __name__ == "__main__":
    add_sample_feedback()
