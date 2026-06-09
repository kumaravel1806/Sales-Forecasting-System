import io
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
from app import create_app  # noqa: E402


def test_admin_upload_csv():
    app = create_app()
    client = app.test_client()

    csv_content = b"date,sku,qty\n2024-01-01,A,1\n2024-01-02,A,2\n"
    data = {
        'file': (io.BytesIO(csv_content), 'sample.csv'),
        'rules': (io.BytesIO(b'{"lowercase_columns": true, "trim_whitespace": true, "drop_duplicates": true}'), ''),
    }
    resp = client.post('/api/admin/upload', data=data, content_type='multipart/form-data')

    assert resp.status_code == 200
    j = resp.get_json()
    assert j.get('success') is True
    assert j['data']['summary_after']['rows'] == 2
