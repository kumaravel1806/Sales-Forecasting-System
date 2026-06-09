import requests
import json

# Test all possible endpoints
endpoints = [
    'http://localhost:8001/api/analytics/dashboard/realtime',
    'http://localhost:8001/api/analytics/realtime/dashboard/simple',
    'http://localhost:8001/api/analytics/realtime/predictive/dashboard',
    'http://localhost:8001/api/health'
]

for endpoint in endpoints:
    try:
        response = requests.get(endpoint, timeout=3)
        print(f'{endpoint}: {response.status_code}')
        if response.status_code == 200:
            data = response.json()
            success = data.get('success')
            print(f'  Success: {success}')
    except Exception as e:
        print(f'{endpoint}: ERROR - {e}')
