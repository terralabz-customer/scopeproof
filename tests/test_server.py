import io
import zipfile

from fastapi.testclient import TestClient

from scopeproof import server


def test_cross_origin_cannot_trigger_local_agent():
    with TestClient(server.app) as client:
        response = client.post('/api/runs', json={'brief': 'Build a one page landing page.'}, headers={'Origin': 'https://untrusted.example'})
        assert response.status_code == 403


def test_unavailable_model_never_returns_fake_result(monkeypatch):
    monkeypatch.delenv('SCOPEPROOF_MODEL', raising=False)
    with TestClient(server.app) as client:
        assert client.get('/api/health').json()['ready'] is False
        result = client.post('/api/runs', json={'brief': 'Build a one page landing page.'})
        assert result.status_code == 503


def test_export_requires_completed_run():
    server.RUNS['test-pending'] = {'id': 'test-pending', 'status': 'running'}
    try:
        with TestClient(server.app) as client:
            assert client.get('/api/runs/test-pending/download').status_code == 409
            assert client.get('/api/runs/unknown/download').status_code == 404
    finally:
        server.RUNS.pop('test-pending', None)


def test_export_preserves_unquoted_state_and_evidence():
    run = {'id': 'export-test', 'brief': 'Add payment checkout.', 'events': [], 'result': {
        'headline': 'Clarification needed', 'quote': {'currency': 'USD', 'total': None},
        'scope_items': [{'status': 'excluded', 'text': 'Checkout', 'evidence': 'Add payment checkout.'}],
        'client_message': 'Please clarify checkout scope.', 'deliverables': ['Review agreed scope']}}
    with zipfile.ZipFile(io.BytesIO(server.build_pack(run))) as archive:
        assert len(archive.namelist()) == 4
        report = archive.read('scope-review.md').decode()
        assert 'Not quoted' in report
        assert 'Add payment checkout.' in report
        assert 'DRAFT FOR HUMAN REVIEW' in report
