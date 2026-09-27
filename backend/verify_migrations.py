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
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=cwd, env=env, check=True)
        subprocess.run([sys.executable, "-c", '''
from fastapi.testclient import TestClient
from app.main import app
from app.database import engine
from sqlalchemy import text
with engine.connect() as connection:
    assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0019"
client = TestClient(app)
response = client.post("/api/v1/auth/register", json={"email": "migration@example.com", "password": "Password123!"})
assert response.status_code == 200, response.text
headers = {"Authorization": "Bearer " + response.json()["data"]["token"]}
response = client.post("/api/v1/blocks", headers=headers, json={"type": "class", "title": "Migration smoke", "day_of_week": 1, "start_time": "09:00", "end_time": "10:00"})
assert response.status_code == 201, response.text
assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
engine.dispose()
print("Fresh migration registration, profile and block smoke checks passed.")
'''], cwd=cwd, env=env, check=True)


if __name__ == "__main__":
    main()
