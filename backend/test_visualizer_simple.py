#!/usr/bin/env python3
"""
Simple test for visualizer functionality
"""
import requests
import os

BASE_URL = "http://localhost:8000"

def test_visualizer_simple():
    """Test visualizer with a simple CSV"""
    print("TESTING VISUALIZER WITH SIMPLE CSV")
    print("=" * 50)
    
    # Create a very simple CSV
    simple_csv = """name,price,sales
Product A,100,50
Product B,200,75
Product C,150,60
Product D,300,90
Product E,250,80"""
    
    try:
        # Test the visualizer endpoint
        files = {'file': ('simple_test.csv', simple_csv, 'text/csv')}
        data = {
            'chart_types': '["bar","pie","line"]',
            'analysis_types': '["summary"]'
        }
        
        print("Sending request to visualizer...")
        response = requests.post(f"{BASE_URL}/api/admin/visualize-data", files=files, data=data)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            try:
                result = response.json()
                print(f"JSON response received: {result.get('success')}")
                
                if result.get('success'):
                    data_section = result.get('data', {})
                    print(f"Data keys: {list(data_section.keys())}")
                    
                    # Check summary
                    summary = data_section.get('summary', {})
                    print(f"Summary: rows={summary.get('rows')}, columns={summary.get('columns')}")
                    
                    # Check charts
                    charts = data_section.get('charts', [])
                    print(f"Charts generated: {len(charts)}")
                    for i, chart in enumerate(charts):
                        print(f"  Chart {i+1}: type={chart.get('type')}, title={chart.get('title')}")
                    
                    # Check analysis
                    analysis = data_section.get('analysis', {})
                    print(f"Analysis keys: {list(analysis.keys())}")
                    
                    return True
                else:
                    error = result.get('meta', {}).get('error', 'Unknown error')
                    print(f"Visualizer failed: {error}")
            except Exception as e:
                print(f"JSON parsing error: {e}")
                print(f"Raw response: {response.text[:500]}")
        else:
            print(f"HTTP error: {response.status_code}")
            print(f"Response text: {response.text[:500]}")
            
    except Exception as e:
        print(f"Request error: {e}")
    
    return False

if __name__ == "__main__":
    success = test_visualizer_simple()
    if success:
        print("\nSUCCESS: Visualizer backend is working!")
        print("The issue might be in the frontend JavaScript.")
    else:
        print("\nFAILED: Visualizer backend has issues.")
