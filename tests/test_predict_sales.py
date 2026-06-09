import os
import sys
import json
from datetime import datetime, timedelta

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from app import create_app  # noqa: E402


def gen_series(n=7, start='2024-01-01', sku='A'):
    start_dt = datetime.fromisoformat(start)
    rows = []
    for i in range(n):
        rows.append({
            'date': (start_dt + timedelta(days=i)).date().isoformat(),
            'qty': i + 1,
            'sku': sku
        })
    return rows


def test_predict_sales_json():
    app = create_app()
    client = app.test_client()
    payload = {
        'horizon': 3,
        'data': gen_series(10)
    }
    resp = client.post('/api/ml/predict/sales', json=payload)
    assert resp.status_code == 200
    j = resp.get_json()
    assert j['success'] is True
    assert 'data' in j and 'results' in j['data']
    assert isinstance(j['data']['results'][0]['forecast'], list)
    assert len(j['data']['results'][0]['forecast']) == 3
