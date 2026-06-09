import requests
import json

print("Testing dashboard realtime endpoint...")
print("=" * 70)

response = requests.get("http://localhost:8000/api/analytics/dashboard/realtime")
print(f"Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print("\nFull Response:")
    print(json.dumps(data, indent=2))
    
    if 'data' in data:
        print("\n\nKPI Structure:")
        if 'kpi' in data['data']:
            print(json.dumps(data['data']['kpi'], indent=2))
        
        print("\n\nAvailable Keys in data:")
        print(list(data['data'].keys()))
else:
    print(f"Error: {response.text}")
