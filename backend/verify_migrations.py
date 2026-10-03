"""Smoke test a fresh Alembic database without accessing local application data.

Run: python verify_migrations.py
Uses a separate process so imported application settings cannot point at a live DB.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    with tempfile.TemporaryDirectory(prefix="syncshift-migrations-") as directory:
        env = os.environ.copy()
        env.update({
            "DATABASE_URL": "sqlite:///" + (Path(directory) / "fresh.db").as_posix(),
            "ENV": "test", "RATE_LIMIT_ENABLED": "false",
            "CAPTCHA_SECRET_KEY": "", "CAPTCHA_ENFORCE": "false",
            "GEMINI_API_KEY": "",
        })
        cwd = Path(__file__).resolve().parent
        env['PYTHONIOENCODING'] = 'utf-8'
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "0019"], cwd=cwd, env=env, check=True)
        subprocess.run([sys.executable, "-c", '''
from datetime import date, time
from app.database import SessionLocal, engine
from app.models import User, Institution, Department, AcademicTerm, AcademicCourse, AcademicSection, SectionEnrollment, Timetable, TimetableVersion, CourseMeeting
from app.models.time_block import TimeBlock
with SessionLocal() as db:
    user = User(email='legacy@example.test', name='Existing learner'); db.add(user); db.flush()
    institution = Institution(name='Existing university', code='OLD'); db.add(institution); db.flush()
    department = Department(institution_id=institution.id,name='Design',code='DES'); db.add(department); db.flush()
    term = AcademicTerm(institution_id=institution.id,name='Fall',academic_year='2026-2027',start_date=date(2026,9,1),end_date=date(2026,12,31)); db.add(term); db.flush()
    course = AcademicCourse(institution_id=institution.id,department_id=department.id,code='DES1',name='Design'); db.add(course); db.flush()
    section = AcademicSection(institution_id=institution.id,course_id=course.id,academic_term_id=term.id,section_code='A'); db.add(section); db.flush()
    db.add(SectionEnrollment(institution_id=institution.id,section_id=section.id,student_id=user.id,status='active'))
    timetable = Timetable(institution_id=institution.id,academic_term_id=term.id,name='Existing timetable',status='active'); db.add(timetable); db.flush()
    version = TimetableVersion(institution_id=institution.id,timetable_id=timetable.id,version_number=1,status='published'); db.add(version); db.flush()
    timetable.published_version_id=version.id
    db.add(CourseMeeting(institution_id=institution.id,timetable_id=timetable.id,version_id=version.id,section_id=section.id,academic_term_id=term.id,day_of_week=1,start_time=time(9),end_time=time(10)))
    db.add(TimeBlock(user_id=user.id,type='shift',title='Existing private work',day_of_week=2,start_time=time(14),end_time=time(16),duration_minutes=120))
    db.commit()
engine.dispose()
'''], cwd=cwd, env=env, check=True)
        env['MIGRATION_COUNTS_PATH'] = str(Path(directory) / 'counts.json')
        subprocess.run([sys.executable, "-c", '''
import json, os
from app.database import engine
from sqlalchemy import text
tables = ['users','time_blocks','academic_sections','section_enrollments','course_meetings','timetable_versions']
with engine.connect() as c:
    counts = {t: c.execute(text('SELECT COUNT(*) FROM '+t)).scalar() for t in tables}
with open(os.environ['MIGRATION_COUNTS_PATH'], 'w') as f: json.dump(counts, f)
engine.dispose()
'''], cwd=cwd, env=env, check=True)
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=cwd, env=env, check=True)
        subprocess.run([sys.executable, "-c", '''
from fastapi.testclient import TestClient
from app.main import app
from app.database import engine
from sqlalchemy import text
import json, os
with engine.connect() as connection:
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0022"
    with open(os.environ['MIGRATION_COUNTS_PATH']) as f: counts = json.load(f)
    for table, count in counts.items():
        assert connection.execute(text('SELECT COUNT(*) FROM '+table)).scalar() == count
    assert connection.execute(text('SELECT COUNT(*) FROM class_workspaces')).scalar() == counts['academic_sections']
client = TestClient(app)
response = client.post("/api/v1/auth/register", json={"email": "migration@example.com", "password": "Password123!"})
assert response.status_code == 200, response.text
headers = {"Authorization": "Bearer " + response.json()["data"]["token"]}
response = client.post("/api/v1/blocks", headers=headers, json={"type": "class", "title": "Migration smoke", "day_of_week": 1, "start_time": "09:00", "end_time": "10:00"})
assert response.status_code == 201, response.text
me_res = client.get("/api/v1/auth/me", headers=headers)
assert me_res.status_code == 200
assert me_res.json()["data"]["time_format"] == "12h"
patch_res = client.patch("/api/v1/auth/me", headers=headers, json={"time_format": "24h", "week_starts_on": "sunday", "planning_hours_start": 8, "planning_hours_end": 17})
assert patch_res.status_code == 200
assert patch_res.json()["data"]["time_format"] == "24h"
assert patch_res.json()["data"]["week_starts_on"] == "sunday"
assert patch_res.json()["data"]["planning_hours_start"] == 8
assert client.post('/api/v1/classes', headers=headers, json={'name':'Migration workspace'}).status_code == 403
engine.dispose()
print("Migration preserves existing users, schedules, enrollments and versions; class, registration, profile and block checks passed.")
'''], cwd=cwd, env=env, check=True)


if __name__ == "__main__":
    main()
