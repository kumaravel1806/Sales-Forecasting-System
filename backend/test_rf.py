from ml.rf_forecast import forecast_sales_random_forest
import pandas as pd
import numpy as np

# Test Random Forest forecast with sample data
dates = pd.date_range('2024-01-01', periods=30, freq='D')
data = []
for i in range(30):
    data.append({
        'date': dates[i].strftime('%Y-%m-%d'),
        'qty': max(10, 50 + i * 2 + np.random.normal(0, 5)),
        'sku': 'TEST001'
    })

df = pd.DataFrame(data)
result = forecast_sales_random_forest(df, horizon=7)
print('Random Forest forecast test successful!')
print('Model:', result["meta"]["model"])
print('Horizon:', result["meta"]["horizon"])
print('Results:', len(result["results"]), 'SKUs')
if result['results']:
    print('Forecast points:', len(result["results"][0]["forecast"]))
