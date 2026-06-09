import io
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from app import create_app  # noqa: E402


def test_reviews_flow_and_sentiment():
    app = create_app()
    client = app.test_client()

    # Create product
    resp = client.post('/api/inventory/products', json={'name': 'Test Product', 'price': 9.99})
    assert resp.status_code == 200
    pid = resp.get_json()['data']['id']

    # Submit review (multipart)
    data = {
        'product_id': str(pid),
        'username': 'alice',
        'rating': '5',
        'text': 'great product!'
    }
    resp = client.post('/api/reviews/submit', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    j = resp.get_json()
    assert j['success'] is True

    # List reviews
    resp = client.get(f'/api/reviews/list?product_id={pid}')
    assert resp.status_code == 200
    j = resp.get_json()
    assert j['success'] is True
    assert any(r['username'] == 'alice' for r in j['data'])

    # Sentiment
    resp = client.post('/api/ml/predict/sentiment', json={'texts': ['amazing quality', 'very bad']})
    assert resp.status_code == 200
    j = resp.get_json()
    assert j['success'] is True
    assert 'results' in j['data']
    assert len(j['data']['results']) == 2
