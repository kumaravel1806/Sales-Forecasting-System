import os
import sys
from flask.testing import FlaskClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from app import create_app  # noqa: E402


def test_health_endpoint():
    app = create_app()
    client: FlaskClient = app.test_client()
    resp = client.get('/api/health')
    assert resp.status_code == 200
    j = resp.get_json()
    assert j.get('success') is True
    assert 'data' in j and 'status' in j['data']
