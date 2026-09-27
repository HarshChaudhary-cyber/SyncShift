import uuid

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def headers():
    response = client.post('/api/v1/auth/register', json={
        'email': f'drag-{uuid.uuid4().hex}@example.com', 'password': 'Password123!',
    })
    assert response.status_code == 200
    return {'Authorization': 'Bearer ' + response.json()['data']['token']}


@pytest.mark.parametrize('scope', ['this', 'future', 'all'])
def test_official_class_move_returns_read_only_error(headers, scope):
    response = client.patch('/api/v1/blocks/-8', headers=headers, json={
        'scope': scope, 'occurrence_date': '2026-09-21',
        'start_time': '13:00', 'end_time': '14:00',
    })
    assert response.status_code == 403
    assert response.json()['error']['code'] == 'official_timetable_read_only'


def test_missing_occurrence_returns_not_found(headers):
    response = client.patch('/api/v1/blocks/99999999', headers=headers, json={
        'scope': 'this', 'occurrence_date': '2026-09-21', 'start_time': '13:00',
    })
    assert response.status_code == 404


def test_personal_drag_persists_date_and_repeated_move_without_duplicates(headers):
    created = client.post('/api/v1/blocks', headers=headers, json={
        'type': 'shift', 'title': 'Drag regression', 'day_of_week': 1,
        'start_time': '10:00', 'end_time': '12:00', 'effective_from': '2026-09-01',
    })
    assert created.status_code == 201
    block_id = created.json()['data']['id']
    for target_date, target_day in [('2026-09-22', 2), ('2026-09-23', 3)]:
        response = client.patch(f'/api/v1/blocks/{block_id}', headers=headers, json={
            'scope': 'this', 'occurrence_date': '2026-09-21', 'override_date': target_date,
            'day_of_week': target_day, 'start_time': '13:00', 'end_time': '15:00',
        })
        assert response.status_code == 200, response.text
        assert response.json()['data']['day_of_week'] == target_day
        blocks = client.get('/api/v1/week?start=2026-09-21', headers=headers).json()['data']['blocks']
        moved = [b for b in blocks if b['id'] == block_id]
        assert len(moved) == 1
        assert moved[0]['occurrence_date'] == target_date
        assert moved[0]['start_time'].startswith('13:00')
    following = client.get('/api/v1/week?start=2026-09-28', headers=headers).json()['data']['blocks']
    unchanged = next(b for b in following if b['id'] == block_id)
    assert unchanged['day_of_week'] == 1
    assert unchanged['start_time'].startswith('10:00')
