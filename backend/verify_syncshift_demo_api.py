"""Exercise a cloned demo database through authenticated HTTP API calls."""
import json
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "syncshift-demo.db"
TARGET = ROOT / "syncshift-e2e.db"
if not SOURCE.exists():
    raise SystemExit("Seed syncshift-demo.db first")
with sqlite3.connect(SOURCE) as src, sqlite3.connect(TARGET) as dst:
    src.backup(dst)
os.environ["DATABASE_URL"] = "sqlite:///./syncshift-e2e.db"
os.environ["ENV"] = "test"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["CAPTCHA_ENFORCE"] = "false"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)
accounts = {a["email"]: a for a in json.loads((ROOT / ".demo-credentials.json").read_text())["accounts"]}


def login(email, identifier=None, institution_id=None):
    payload = {"identifier": identifier or email, "password": accounts[email]["password"]}
    if institution_id:
        payload["institution_id"] = institution_id
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200, (email, response.text)
    return response.json()["data"]


def headers(identity):
    return {"Authorization": f"Bearer {identity['token']}"}


admin = login("admin@ssdemo.example")
professor = login("professor.asha@ssdemo.example")
arjun = login("student.arjun@ssdemo.example")
meera = login("student.meera@ssdemo.example")
kabir = login("student.kabir@riverdemo.example")
assert login("student.arjun@ssdemo.example", "00041001", admin["institution_id"])["user_id"] == arjun["user_id"]
assert login("student.kabir@riverdemo.example", "00041001", kabir["institution_id"])["user_id"] == kabir["user_id"]
missing_context = client.post("/api/v1/auth/login", json={"identifier": "00041001", "password": accounts["student.arjun@ssdemo.example"]["password"]})
assert missing_context.status_code == 400
assert client.get(f"/api/v1/academic-admin/{admin['institution_id']}/users", headers=headers(arjun)).status_code == 403

classes = client.get("/api/v1/classes", headers=headers(professor)).json()["data"]
assert len([c for c in classes if c.get("section_id")]) >= 2
class_id = next(c["id"] for c in classes if c.get("section_id"))
assert client.get(f"/api/v1/classes/{class_id}", headers=headers(arjun)).status_code == 200
assert client.get(f"/api/v1/classes/{class_id}", headers=headers(meera)).status_code in (403, 404)
assert client.get(f"/api/v1/classes/{class_id}", headers=headers(kabir)).status_code in (403, 404)

event_date = date.today() + timedelta(days=10)
event = {"title": "API verification seminar", "location": "Demo room", "event_date": event_date.isoformat(), "start_time": "18:00", "end_time": "19:00"}
created = client.post(f"/api/v1/classes/{class_id}/events", json=event, headers=headers(professor))
assert created.status_code == 201, created.text
event_id = created.json()["data"]["id"]
week = event_date - timedelta(days=event_date.weekday())
calendar = f"/api/v1/week?start={week.isoformat()}"
def visible(identity):
    response = client.get(calendar, headers=headers(identity))
    assert response.status_code == 200, response.text
    return any(b["title"] == event["title"] for b in response.json()["data"]["blocks"])
assert not visible(arjun)
assert client.patch(f"/api/v1/classes/{class_id}/events/{event_id}", json=event, headers=headers(arjun)).status_code in (403, 404)
published = client.post(f"/api/v1/classes/{class_id}/events/{event_id}/publish", headers=headers(professor))
assert published.status_code == 200, published.text
assert visible(arjun) and visible(professor)
assert not visible(meera) and not visible(kabir)

with sqlite3.connect(TARGET) as db:
    section_id = db.execute("select section_id from class_workspaces where id=?", (class_id,)).fetchone()[0]
assignment = client.post(f"/api/v1/academic-admin/{admin['institution_id']}/assignments", json={"user_id": meera["user_id"], "section_id": section_id, "active": True}, headers=headers(admin))
assert assignment.status_code == 200, assignment.text
assert visible(meera)
removed = client.post(f"/api/v1/academic-admin/{admin['institution_id']}/assignments", json={"user_id": meera["user_id"], "section_id": section_id, "active": False}, headers=headers(admin))
assert removed.status_code == 200, removed.text
assert not visible(meera)

# Teaching assignment changes are observed through the professor's next API read.
with sqlite3.connect(TARGET) as db:
    extra = db.execute("select s.id, w.id from academic_sections s join class_workspaces w on w.section_id=s.id where s.section_code='CS301-SEC-A'").fetchone()
assert extra
section_extra, class_extra = extra
assert client.get(f"/api/v1/classes/{class_extra}", headers=headers(professor)).status_code in (403, 404)
assert client.post(f"/api/v1/academic-admin/{admin['institution_id']}/assignments", json={"user_id": professor["user_id"], "section_id": section_extra, "active": True}, headers=headers(admin)).status_code == 200
assert client.get(f"/api/v1/classes/{class_extra}", headers=headers(professor)).status_code == 200
assert client.post(f"/api/v1/academic-admin/{admin['institution_id']}/assignments", json={"user_id": professor["user_id"], "section_id": section_extra, "active": False}, headers=headers(admin)).status_code == 200
assert client.get(f"/api/v1/classes/{class_extra}", headers=headers(professor)).status_code in (403, 404)

def task_titles(identity):
    response = client.get("/api/v1/tasks", headers=headers(identity))
    assert response.status_code == 200, response.text
    return {task["title"] for task in response.json()["data"]}

student_private = "Implement Red-Black Tree in C++"
professor_private = "Finalize Midterm Exam Questions & Solutions"
assert student_private in task_titles(arjun)
assert professor_private in task_titles(professor)
assert professor_private not in task_titles(arjun)
assert student_private not in task_titles(professor)
assert student_private not in task_titles(admin) and professor_private not in task_titles(admin)
print("PASS: email and scoped identifier login; admin denial; class draft/publish/calendar; tenant isolation; enrolment and professor assignment add/remove; private task isolation")
