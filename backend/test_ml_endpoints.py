import requests
import json

# Test ML endpoints with all three algorithms
base_url = 'http://localhost:8001/api/ml'

# Test model comparison endpoint
try:
    sample_data = {
        'data': [
            {'date': '2024-01-01', 'qty': 50, 'sku': 'TEST001'},
            {'date': '2024-01-02', 'qty': 55, 'sku': 'TEST001'},
            {'date': '2024-01-03', 'qty': 52, 'sku': 'TEST001'},
            {'date': '2024-01-04', 'qty': 58, 'sku': 'TEST001'},
            {'date': '2024-01-05', 'qty': 60, 'sku': 'TEST001'},
            {'date': '2024-01-06', 'qty': 62, 'sku': 'TEST001'},
            {'date': '2024-01-07', 'qty': 65, 'sku': 'TEST001'},
            {'date': '2024-01-08', 'qty': 63, 'sku': 'TEST001'},
            {'date': '2024-01-09', 'qty': 68, 'sku': 'TEST001'},
            {'date': '2024-01-10', 'qty': 70, 'sku': 'TEST001'}
        ],
        'horizon': 3
    }
    
    response = requests.post(f'{base_url}/compare', json=sample_data)
    result = response.json()
    
    print('ML Model Comparison Test:')
    print('Status:', 'SUCCESS' if result.get('success') else 'FAILED')
    if result.get('success'):
        models = result.get('data', {}).get('overall', {})
        print('Available models:', list(models.keys()))
        for model, metrics in models.items():
            if metrics:
                mae = metrics.get('mae', 'N/A')
                print(f'{model.upper()}: MAE={mae}')
    else:
        print('Error:', result.get('meta', {}).get('error'))
        
except Exception as e:
    print('Test failed:', str(e))
