"""Exercise a cloned demo database through authenticated HTTP API calls."""
import json
import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = ROOT / "syncshift-roles-demo.db" if (ROOT / "syncshift-roles-demo.db").exists() else ROOT / "syncshift-demo.db"
TARGET = ROOT / "syncshift-e2e.db"
if not SOURCE.exists():
    raise SystemExit("Seed demo database first (syncshift-roles-demo.db or syncshift-demo.db)")
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


admin = login("admin.demo@ssdemo.example")
teacher1 = login("teacher.one@ssdemo.example")
teacher2 = login("teacher.two@ssdemo.example")
student1 = login("student.one@ssdemo.example")
student2 = login("student.two@ssdemo.example")

# Enrollment logins
assert login("student.one@ssdemo.example", "00041001", admin["institution_id"])["user_id"] == student1["user_id"]
assert login("student.two@ssdemo.example", "00041002", admin["institution_id"])["user_id"] == student2["user_id"]

# Student cannot access admin APIs
assert client.get(f"/api/v1/academic-admin/{admin['institution_id']}/users", headers=headers(student1)).status_code == 403
assert client.get(f"/api/v1/academic-admin/{admin['institution_id']}/users", headers=headers(teacher1)).status_code == 403

# Teacher 1 classes
classes = client.get("/api/v1/classes", headers=headers(teacher1)).json()["data"]
assert len([c for c in classes if c.get("section_id")]) >= 2
class_id = next(c["id"] for c in classes if c.get("section_id"))
assert client.get(f"/api/v1/classes/{class_id}", headers=headers(student1)).status_code == 200
# student2 is not in CS101, so access is rejected
assert client.get(f"/api/v1/classes/{class_id}", headers=headers(student2)).status_code in (403, 404)

event_date = date.today() + timedelta(days=10)
event = {"title": "API verification seminar", "location": "Demo room", "event_date": event_date.isoformat(), "start_time": "18:00", "end_time": "19:00"}
created = client.post(f"/api/v1/classes/{class_id}/events", json=event, headers=headers(teacher1))
assert created.status_code == 201, created.text
event_id = created.json()["data"]["id"]
week = event_date - timedelta(days=event_date.weekday())
calendar = f"/api/v1/week?start={week.isoformat()}"


def visible(identity):
    response = client.get(calendar, headers=headers(identity))
    assert response.status_code == 200, response.text
    return any(b["title"] == event["title"] for b in response.json()["data"]["blocks"])


assert not visible(student1)
assert client.patch(f"/api/v1/classes/{class_id}/events/{event_id}", json=event, headers=headers(student1)).status_code in (403, 404)
published = client.post(f"/api/v1/classes/{class_id}/events/{event_id}/publish", headers=headers(teacher1))
assert published.status_code == 200, published.text
assert visible(student1) and visible(teacher1)
assert not visible(student2)

# Task isolation
def task_titles(identity):
    response = client.get("/api/v1/tasks", headers=headers(identity))
    assert response.status_code == 200, response.text
    return {task["title"] for task in response.json()["data"]}


student1_private = "Implement Red-Black Tree in C++"
teacher1_private = "Finalize Midterm Exam Questions & Solutions"
student2_private = "Discrete Probability Problem Set"

assert student1_private in task_titles(student1)
assert teacher1_private in task_titles(teacher1)
assert student2_private in task_titles(student2)
assert teacher1_private not in task_titles(student1)
assert student1_private not in task_titles(teacher1)
assert student2_private not in task_titles(student1)
assert student1_private not in task_titles(admin) and teacher1_private not in task_titles(admin)
print("PASS: 5 role accounts authenticated; enrollment login verified; student and teacher access boundaries enforced; class draft/publish/calendar verified; private task isolation verified")
