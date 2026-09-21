"""Live Docker validation script for Scenarios A, B, C, D."""
import sys
import uuid
import pytest
import requests

API_URL = "http://localhost:8000/api/v1"
MOCK_CAPTCHA = "mock_captcha_pass_test"


def _is_live_server_running() -> bool:
    try:
        r = requests.get("http://localhost:8000/api/v1/health", timeout=0.5)
        return r.status_code == 200
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _is_live_server_running(),
    reason="Live server on localhost:8000 is not running (start containers/server to run live tests)",
)

def test_scenario_a():
    print("\n--- Running Scenario A: Student Signup & Login ---")
    email = f"live_student_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "StudentPassword123!"
    
    # 1. Register public user
    reg_res = requests.post(f"{API_URL}/auth/register", json={
        "email": email,
        "password": pwd,
        "confirm_password": pwd,
        "timezone": "UTC",
        "captcha_token": MOCK_CAPTCHA
    })
    assert reg_res.status_code == 200, f"Register failed: {reg_res.text}"
    user_data = reg_res.json()["data"]
    print(f"Registered user: {user_data['email']}, role in response: {user_data.get('institution_role')}")
    assert user_data.get("institution_role") is None
    
    # 2. Login
    login_res = requests.post(f"{API_URL}/auth/login", json={
        "email": email,
        "password": pwd,
        "captcha_token": MOCK_CAPTCHA
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    login_data = login_res.json()["data"]
    token = login_data["token"]
    role = login_data.get("institution_role")
    print(f"Logged in user role: {role}")
    assert role is None
    
    # Routing decision logic
    portal = "/university/dashboard" if role in ("faculty", "professor", "admin", "super_admin") else "/student/dashboard"
    print(f"Portal redirect computed: {portal}")
    assert portal == "/student/dashboard", f"Expected /student/dashboard, got {portal}"
    print("Scenario A: SUCCESS")
    return token, email

def test_scenario_b():
    print("\n--- Running Scenario B: University Account Login ---")
    admin_email = f"live_admin_{uuid.uuid4().hex[:8]}@northbridge.edu"
    pwd = "AdminPassword123!"
    inst_code = f"NB_{uuid.uuid4().hex[:6].upper()}"
    
    # Register user
    reg_res = requests.post(f"{API_URL}/auth/register", json={
        "email": admin_email,
        "password": pwd,
        "confirm_password": pwd,
        "timezone": "UTC",
        "captcha_token": MOCK_CAPTCHA
    })
    assert reg_res.status_code == 200, f"Admin register failed: {reg_res.text}"
    token = reg_res.json()["data"]["token"]
    
    # Provision institution -> creator becomes 'admin'
    inst_res = requests.post(
        f"{API_URL}/institutions",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": f"Northbridge University {uuid.uuid4().hex[:4]}",
            "code": inst_code,
            "timezone": "Europe/London"
        }
    )
    assert inst_res.status_code == 201, f"Institution creation failed: {inst_res.text}"
    inst_id = inst_res.json()["data"]["id"]
    print(f"Created institution: ID={inst_id}, Code={inst_code}")
    
    # Now login again as this user
    login_res = requests.post(f"{API_URL}/auth/login", json={
        "email": admin_email,
        "password": pwd,
        "captcha_token": MOCK_CAPTCHA
    })
    assert login_res.status_code == 200, f"Admin login failed: {login_res.text}"
    login_data = login_res.json()["data"]
    role = login_data.get("institution_role")
    print(f"Admin login returned institution_role: {role}")
    assert role == "admin", f"Expected admin, got {role}"
    
    portal = "/university/dashboard" if role in ("faculty", "professor", "admin", "super_admin") else "/student/dashboard"
    print(f"Portal redirect computed: {portal}")
    assert portal == "/university/dashboard", f"Expected /university/dashboard, got {portal}"
    
    # Add a faculty member to this institution
    faculty_email = f"live_faculty_{uuid.uuid4().hex[:8]}@northbridge.edu"
    fac_pwd = "FacultyPassword123!"
    fac_reg = requests.post(f"{API_URL}/auth/register", json={
        "email": faculty_email,
        "password": fac_pwd,
        "confirm_password": fac_pwd,
        "timezone": "UTC",
        "captcha_token": MOCK_CAPTCHA
    })
    assert fac_reg.status_code == 200, f"Faculty register failed: {fac_reg.text}"
    fac_user_id = fac_reg.json()["data"]["user_id"]
    
    # Admin provisions faculty
    add_mem_res = requests.post(
        f"{API_URL}/institutions/{inst_id}/members",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": fac_user_id, "role": "faculty"}
    )
    assert add_mem_res.status_code == 201, f"Adding faculty failed: {add_mem_res.text}"
    print(f"Provisioned faculty member: {faculty_email}")
    
    # Faculty login
    fac_login_res = requests.post(f"{API_URL}/auth/login", json={
        "email": faculty_email,
        "password": fac_pwd,
        "captcha_token": MOCK_CAPTCHA
    })
    assert fac_login_res.status_code == 200, f"Faculty login failed: {fac_login_res.text}"
    fac_data = fac_login_res.json()["data"]
    fac_role = fac_data.get("institution_role")
    print(f"Faculty login returned institution_role: {fac_role}")
    assert fac_role == "faculty", f"Expected faculty, got {fac_role}"
    
    fac_portal = "/university/dashboard" if fac_role in ("faculty", "professor", "admin", "super_admin") else "/student/dashboard"
    print(f"Faculty portal redirect computed: {fac_portal}")
    assert fac_portal == "/university/dashboard", f"Expected /university/dashboard, got {fac_portal}"
    print("Scenario B: SUCCESS")
    return inst_id

def test_scenario_c(student_token, inst_id):
    print("\n--- Running Scenario C: Student Tries University Endpoint ---")
    res = requests.get(
        f"{API_URL}/institutions/{inst_id}/members",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    print(f"Student access response code: {res.status_code} (expected 403)")
    assert res.status_code == 403, f"Expected 403 Forbidden, got {res.status_code}: {res.text}"
    print("Scenario C: SUCCESS (Direct university access correctly blocked)")

def test_scenario_d(student_token):
    print("\n--- Running Scenario D: Frontend Payload Manipulation ---")
    patch_res = requests.patch(
        f"{API_URL}/auth/me",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"role": "super_admin", "institution_role": "admin"}
    )
    print(f"PATCH /me response code: {patch_res.status_code}")
    assert patch_res.status_code == 200
    res_data = patch_res.json()["data"]
    print(f"Role after attempted escalation: {res_data.get('institution_role')}")
    assert res_data.get("institution_role") is None, "Privilege escalation succeeded! Security flaw!"
    
    me_res = requests.get(
        f"{API_URL}/auth/me",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert me_res.status_code == 200
    assert me_res.json()["data"].get("institution_role") is None
    print("Scenario D: SUCCESS (Role modification rejected/ignored by backend)")

if __name__ == "__main__":
    s_token, s_email = test_scenario_a()
    inst_id = test_scenario_b()
    test_scenario_c(s_token, inst_id)
    test_scenario_d(s_token)
    print("\n================ ALL LIVE DOCKER SCENARIOS PASSED ================")
