import requests
import json

# Test the realtime dashboard endpoint
try:
    response = requests.get('http://localhost:8001/api/analytics/realtime/dashboard/simple', timeout=5)
    print(f'Status Code: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print('✅ Endpoint working!')
        print('Success:', data.get('success'))
        if data.get('success'):
            metrics = data.get('data', {})
            print('Products:', metrics.get('total_products', 'N/A'))
            print('Orders today:', metrics.get('today_orders', 'N/A'))
            print('Revenue today:', metrics.get('today_revenue', 'N/A'))
    else:
        print('Error:', response.text)
        
except requests.exceptions.ConnectionError:
    print('❌ Server not running on localhost:8001')
except Exception as e:
    print('❌ Error:', e)
