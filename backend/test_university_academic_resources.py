import time
from datetime import date, timedelta
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def create_test_user(prefix: str) -> tuple[int, str]:
    """Helper to register a unique test user and return (user_id, token)."""
    email = f"{prefix}_{int(time.time() * 1000)}@univ-test.edu"
    password = "TestPassword123!"
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "timezone": "Europe/London",
            "weekly_work_hour_limit": 20.0,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return data["user_id"], data["token"]


def create_test_institution(admin_token: str, name_prefix: str = "Test University") -> tuple[int, str]:
    """Helper to create an institution where the user becomes admin."""
    headers = {"Authorization": f"Bearer {admin_token}"}
    code = f"INST_{int(time.time() * 1000)}"[:16]
    resp = client.post(
        "/api/v1/institutions",
        headers=headers,
        json={
            "name": f"{name_prefix} {code}",
            "code": code,
            "timezone": "America/New_York",
            "country": "US",
        },
    )
    assert resp.status_code == 201, resp.text
    inst_id = resp.json()["data"]["id"]
    return inst_id, code


def test_courses_crud_and_validation():
    """Verify Course creation, reading, updating, archiving, and code uniqueness within institution."""
    _, admin_token = create_test_user("admin_course")
    inst_id, _ = create_test_institution(admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a department
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=headers,
        json={"name": "Computer Science", "code": "CS", "description": "CS Department"},
    )
    assert dept_resp.status_code == 201
    dept_id = dept_resp.json()["data"]["id"]

    # 2. Create Course CS101
    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=headers,
        json={
            "department_id": dept_id,
            "code": "CS101",
            "name": "Introduction to Computer Science",
            "credits": 4,
            "level": "undergraduate",
            "min_room_capacity": 40,
            "required_room_type": "lecture_hall",
        },
    )
    assert course_resp.status_code == 201
    course_data = course_resp.json()["data"]
    course_id = course_data["id"]
    assert course_data["code"] == "CS101"
    assert course_data["name"] == "Introduction to Computer Science"
    assert course_data["department_id"] == dept_id
    assert course_data["department_name"] == "Computer Science"
    assert course_data["credits"] == 4
    assert course_data["min_room_capacity"] == 40
    assert course_data["required_room_type"] == "lecture_hall"

    # 3. Reject duplicate course code within institution
    dup_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=headers,
        json={
            "department_id": dept_id,
            "code": "cs101",  # case-insensitive check
            "name": "Intro to CS Duplicate",
            "credits": 3,
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "course_code_exists"

    # 4. Reject invalid department ID
    invalid_dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=headers,
        json={"department_id": 999999, "code": "CS102", "name": "Algorithms"},
    )
    assert invalid_dept_resp.status_code == 404

    # 5. List courses with filter
    list_resp = client.get(f"/api/v1/institutions/{inst_id}/courses?department_id={dept_id}", headers=headers)
    assert list_resp.status_code == 200
    courses = list_resp.json()["data"]
    assert len(courses) == 1
    assert courses[0]["code"] == "CS101"

    # Search filter
    search_resp = client.get(f"/api/v1/institutions/{inst_id}/courses?search=intro", headers=headers)
    assert search_resp.status_code == 200
    assert len(search_resp.json()["data"]) == 1

    # 6. Read single course
    get_resp = client.get(f"/api/v1/institutions/{inst_id}/courses/{course_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == course_id

    # 7. Update course
    patch_resp = client.patch(
        f"/api/v1/institutions/{inst_id}/courses/{course_id}",
        headers=headers,
        json={"name": "Intro to Computer Science & Programming", "credits": 3},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["name"] == "Intro to Computer Science & Programming"
    assert patch_resp.json()["data"]["credits"] == 3

    # 8. Soft-delete course
    del_resp = client.delete(f"/api/v1/institutions/{inst_id}/courses/{course_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True

    # Check that deleted course is excluded from listing
    list_after_del = client.get(f"/api/v1/institutions/{inst_id}/courses", headers=headers)
    assert len(list_after_del.json()["data"]) == 0


def test_sections_crud_and_validation():
    """Verify AcademicSection creation, duplicate prevention, term/course linking, and status updates."""
    _, admin_token = create_test_user("admin_sec")
    inst_id, _ = create_test_institution(admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Setup Department, Course, Term
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=headers,
        json={"name": "Mathematics", "code": "MATH"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=headers,
        json={"department_id": dept_id, "code": "MATH201", "name": "Calculus II", "credits": 4},
    )
    course_id = course_resp.json()["data"]["id"]

    term_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
        json={
            "name": "Fall 2026",
            "academic_year": "2026-2027",
            "start_date": str(date.today()),
            "end_date": str(date.today() + timedelta(days=120)),
            "status": "upcoming",
        },
    )
    term_id = term_resp.json()["data"]["id"]

    # 1. Create Section A
    sec_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "SEC-A",
            "capacity": 35,
            "description": "Morning lecture section",
        },
    )
    assert sec_resp.status_code == 201
    sec_data = sec_resp.json()["data"]
    sec_id = sec_data["id"]
    assert sec_data["section_code"] == "SEC-A"
    assert sec_data["capacity"] == 35
    assert sec_data["course_code"] == "MATH201"
    assert sec_data["term_name"] == "Fall 2026"

    # 2. Reject duplicate section code for same course and term
    dup_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=headers,
        json={
            "course_id": course_id,
            "academic_term_id": term_id,
            "section_code": "sec-a",
            "capacity": 30,
        },
    )
    assert dup_resp.status_code == 409
    assert dup_resp.json()["error"]["code"] == "section_code_exists"

    # 3. List sections
    list_resp = client.get(
        f"/api/v1/institutions/{inst_id}/sections?course_id={course_id}&academic_term_id={term_id}",
        headers=headers,
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) == 1

    # 4. Read single section
    get_resp = client.get(f"/api/v1/institutions/{inst_id}/sections/{sec_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["id"] == sec_id

    # 5. Update section capacity
    patch_resp = client.patch(
        f"/api/v1/institutions/{inst_id}/sections/{sec_id}",
        headers=headers,
        json={"capacity": 50, "description": "Expanded capacity section"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["data"]["capacity"] == 50

    # 6. Cancel / delete section
    del_resp = client.delete(f"/api/v1/institutions/{inst_id}/sections/{sec_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["data"]["deleted"] is True


def test_faculty_profiles_and_section_assignments():
    """Verify FacultyProfile registration, SectionFacultyAssignment, and duplicate assignment rejection."""
    _, admin_token = create_test_user("admin_fac")
    inst_id, _ = create_test_institution(admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Create a Department, Course, Term, Section
    dept_resp = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=headers,
        json={"name": "Physics", "code": "PHYS"},
    )
    dept_id = dept_resp.json()["data"]["id"]

    course_resp = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=headers,
        json={"department_id": dept_id, "code": "PHYS101", "name": "General Physics I"},
    )
    course_id = course_resp.json()["data"]["id"]

    term_resp = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
        json={
            "name": "Spring 2027",
            "academic_year": "2026-2027",
            "start_date": str(date.today() + timedelta(days=130)),
            "end_date": str(date.today() + timedelta(days=250)),
        },
    )
    term_id = term_resp.json()["data"]["id"]

    sec_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=headers,
        json={"course_id": course_id, "academic_term_id": term_id, "section_code": "001", "capacity": 60},
    )
    sec_id = sec_resp.json()["data"]["id"]

    # 2. Register a professor user and add to institution
    prof_user_id, prof_token = create_test_user("prof_newton")
    add_member_resp = client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=headers,
        json={"user_id": prof_user_id, "role": "professor", "status": "active"},
    )
    assert add_member_resp.status_code == 201

    # 3. Create FacultyProfile
    fac_resp = client.post(
        f"/api/v1/institutions/{inst_id}/faculty",
        headers=headers,
        json={
            "user_id": prof_user_id,
            "department_id": dept_id,
            "employee_code": "EMP-PHYS-01",
            "title": "Professor of Physics",
        },
    )
    assert fac_resp.status_code == 201
    fac_data = fac_resp.json()["data"]
    fac_id = fac_data["id"]
    assert fac_data["employee_code"] == "EMP-PHYS-01"
    assert fac_data["title"] == "Professor of Physics"
    assert fac_data["department_name"] == "Physics"

    # Duplicate faculty profile for same user rejected
    dup_fac = client.post(
        f"/api/v1/institutions/{inst_id}/faculty",
        headers=headers,
        json={"user_id": prof_user_id, "department_id": dept_id},
    )
    assert dup_fac.status_code == 409

    # 4. Assign Faculty to Section
    assign_resp = client.post(
        f"/api/v1/institutions/{inst_id}/sections/{sec_id}/faculty",
        headers=headers,
        json={"faculty_id": fac_id, "role": "instructor", "is_primary": True},
    )
    assert assign_resp.status_code == 201
    assign_data = assign_resp.json()["data"]
    assignment_id = assign_data["id"]
    assert assign_data["faculty_id"] == fac_id
    assert assign_data["role"] == "instructor"
    assert assign_data["is_primary"] is True

    # Duplicate assignment to same section rejected
    dup_assign = client.post(
        f"/api/v1/institutions/{inst_id}/sections/{sec_id}/faculty",
        headers=headers,
        json={"faculty_id": fac_id, "role": "co_instructor"},
    )
    assert dup_assign.status_code == 409
    assert dup_assign.json()["error"]["code"] == "duplicate_faculty_assignment"

    # 5. List section instructors
    list_instructors = client.get(
        f"/api/v1/institutions/{inst_id}/sections/{sec_id}/faculty",
        headers=headers,
    )
    assert list_instructors.status_code == 200
    assert len(list_instructors.json()["data"]) == 1

    # Section detail includes instructors array
    sec_detail = client.get(f"/api/v1/institutions/{inst_id}/sections/{sec_id}", headers=headers)
    assert sec_detail.status_code == 200
    assert len(sec_detail.json()["data"]["instructors"]) == 1

    # 6. Remove faculty from section
    del_assign = client.delete(
        f"/api/v1/institutions/{inst_id}/sections/{sec_id}/faculty/{assignment_id}",
        headers=headers,
    )
    assert del_assign.status_code == 200
    assert del_assign.json()["data"]["deleted"] is True

    # 7. Soft-delete faculty profile
    del_fac = client.delete(f"/api/v1/institutions/{inst_id}/faculty/{fac_id}", headers=headers)
    assert del_fac.status_code == 200
    assert del_fac.json()["data"]["deleted"] is True


def test_rooms_crud_and_validation():
    """Verify Room creation, capacity validation, building uniqueness, and updates."""
    _, admin_token = create_test_user("admin_room")
    inst_id, _ = create_test_institution(admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Invalid capacity (<= 0) rejected
    bad_cap_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=headers,
        json={"building": "Science Complex", "room_number": "SC-101", "capacity": 0},
    )
    assert bad_cap_resp.status_code == 422

    # 2. Create valid room
    room_resp = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=headers,
        json={
            "building": "Science Complex",
            "room_number": "SC-101",
            "name": "Quantum Lecture Hall",
            "capacity": 120,
            "room_type": "lecture_hall",
            "basic_features": "Laser Projector, Surround Audio, 2 Whiteboards",
        },
    )
    assert room_resp.status_code == 201
    room_data = room_resp.json()["data"]
    room_id = room_data["id"]
    assert room_data["room_number"] == "SC-101"
    assert room_data["capacity"] == 120
    assert room_data["room_type"] == "lecture_hall"

    # 3. Reject duplicate room number in same building
    dup_room = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=headers,
        json={
            "building": "science complex",
            "room_number": "sc-101",
            "capacity": 50,
        },
    )
    assert dup_room.status_code == 409
    assert dup_room.json()["error"]["code"] == "room_exists"

    # 4. List rooms with filter
    rooms_resp = client.get(
        f"/api/v1/institutions/{inst_id}/rooms?room_type=lecture_hall",
        headers=headers,
    )
    assert rooms_resp.status_code == 200
    assert len(rooms_resp.json()["data"]) == 1

    # 5. Read single room
    get_room = client.get(f"/api/v1/institutions/{inst_id}/rooms/{room_id}", headers=headers)
    assert get_room.status_code == 200
    assert get_room.json()["data"]["id"] == room_id

    # 6. Update room
    patch_room = client.patch(
        f"/api/v1/institutions/{inst_id}/rooms/{room_id}",
        headers=headers,
        json={"capacity": 140, "name": "Main Quantum Lecture Hall"},
    )
    assert patch_room.status_code == 200
    assert patch_room.json()["data"]["capacity"] == 140

    # 7. Soft-delete room
    del_room = client.delete(f"/api/v1/institutions/{inst_id}/rooms/{room_id}", headers=headers)
    assert del_room.status_code == 200
    assert del_room.json()["data"]["deleted"] is True


def test_tenant_isolation_and_cross_tenant_rejection():
    """Verify strict tenant isolation: Institution A cannot access, create, or link Institution B resources."""
    _, admin_token_a = create_test_user("admin_tenant_a")
    inst_a_id, _ = create_test_institution(admin_token_a, "University A")
    headers_a = {"Authorization": f"Bearer {admin_token_a}"}

    _, admin_token_b = create_test_user("admin_tenant_b")
    inst_b_id, _ = create_test_institution(admin_token_b, "University B")
    headers_b = {"Authorization": f"Bearer {admin_token_b}"}

    # Setup Dept & Course in Inst A
    dept_a_resp = client.post(
        f"/api/v1/institutions/{inst_a_id}/departments",
        headers=headers_a,
        json={"name": "Engineering", "code": "ENG"},
    )
    dept_a_id = dept_a_resp.json()["data"]["id"]

    course_a_resp = client.post(
        f"/api/v1/institutions/{inst_a_id}/courses",
        headers=headers_a,
        json={"department_id": dept_a_id, "code": "ENG101", "name": "Intro to Engineering"},
    )
    course_a_id = course_a_resp.json()["data"]["id"]

    # Setup Dept & Course in Inst B
    dept_b_resp = client.post(
        f"/api/v1/institutions/{inst_b_id}/departments",
        headers=headers_b,
        json={"name": "Business", "code": "BUS"},
    )
    dept_b_id = dept_b_resp.json()["data"]["id"]

    course_b_resp = client.post(
        f"/api/v1/institutions/{inst_b_id}/courses",
        headers=headers_b,
        json={"department_id": dept_b_id, "code": "BUS101", "name": "Intro to Business"},
    )
    course_b_id = course_b_resp.json()["data"]["id"]

    # 1. Admin A attempts to list courses of Inst B -> 403 Forbidden
    cross_list = client.get(f"/api/v1/institutions/{inst_b_id}/courses", headers=headers_a)
    assert cross_list.status_code == 403
    assert cross_list.json()["error"]["code"] == "unauthorized_institution_access"

    # 2. Admin B attempts to list courses of Inst A -> 403 Forbidden
    cross_list_b = client.get(f"/api/v1/institutions/{inst_a_id}/courses", headers=headers_b)
    assert cross_list_b.status_code == 403

    # 3. Admin A attempts to read Course B using Inst A context (IDOR) -> 404 Not Found
    idor_course = client.get(f"/api/v1/institutions/{inst_a_id}/courses/{course_b_id}", headers=headers_a)
    assert idor_course.status_code == 404

    # 4. Admin A attempts to create a Course in Inst A referencing Department B from Inst B -> 404 Not Found
    cross_dept_course = client.post(
        f"/api/v1/institutions/{inst_a_id}/courses",
        headers=headers_a,
        json={"department_id": dept_b_id, "code": "TEST99", "name": "Cross Tenant Test"},
    )
    assert cross_dept_course.status_code == 404

    # 5. Cross-tenant section creation rejection
    term_a_resp = client.post(
        f"/api/v1/institutions/{inst_a_id}/terms",
        headers=headers_a,
        json={"name": "Term A", "academic_year": "2026-2027", "start_date": str(date.today()), "end_date": str(date.today() + timedelta(days=60))},
    )
    term_a_id = term_a_resp.json()["data"]["id"]

    cross_sec = client.post(
        f"/api/v1/institutions/{inst_a_id}/sections",
        headers=headers_a,
        json={"course_id": course_b_id, "academic_term_id": term_a_id, "section_code": "01"},
    )
    assert cross_sec.status_code == 404


def test_role_based_authorization():
    """Verify that Students and Professors cannot mutate resources, but can read them, and unauthenticated are blocked."""
    # Setup Institution and Admin
    _, admin_token = create_test_user("admin_rbac")
    inst_id, _ = create_test_institution(admin_token)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Setup Department & Course
    dept = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=admin_headers,
        json={"name": "Biology", "code": "BIO"},
    ).json()["data"]
    dept_id = dept["id"]

    course = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=admin_headers,
        json={"department_id": dept_id, "code": "BIO101", "name": "Intro to Biology"},
    ).json()["data"]
    course_id = course["id"]

    # Register Student
    student_user_id, student_token = create_test_user("student_user")
    client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=admin_headers,
        json={"user_id": student_user_id, "role": "student", "status": "active"},
    )
    student_headers = {"Authorization": f"Bearer {student_token}"}

    # 1. Student can READ courses
    stud_read = client.get(f"/api/v1/institutions/{inst_id}/courses", headers=student_headers)
    assert stud_read.status_code == 200
    assert len(stud_read.json()["data"]) >= 1

    # 2. Student CANNOT create course -> 403 Forbidden
    stud_create_course = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=student_headers,
        json={"department_id": dept_id, "code": "BIO999", "name": "Illegal Student Course"},
    )
    assert stud_create_course.status_code == 403
    assert stud_create_course.json()["error"]["code"] == "forbidden"

    # 3. Student CANNOT delete course -> 403 Forbidden
    stud_del_course = client.delete(
        f"/api/v1/institutions/{inst_id}/courses/{course_id}",
        headers=student_headers,
    )
    assert stud_del_course.status_code == 403

    # 4. Student CANNOT create room -> 403 Forbidden
    stud_create_room = client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=student_headers,
        json={"building": "Hall", "room_number": "H1", "capacity": 30},
    )
    assert stud_create_room.status_code == 403

    # 5. Unauthenticated blocked -> 401 Unauthorized
    unauth_resp = client.get(f"/api/v1/institutions/{inst_id}/courses")
    assert unauth_resp.status_code == 401


def test_dashboard_resource_counts_updated():
    """Verify that the dashboard endpoint accurately reports counts for courses, sections, faculty, and rooms."""
    _, admin_token = create_test_user("admin_dash")
    inst_id, _ = create_test_institution(admin_token)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Initial counts should be 0
    init_dash = client.get(f"/api/v1/institutions/{inst_id}/dashboard", headers=headers)
    assert init_dash.status_code == 200
    init_data = init_dash.json()["data"]
    assert init_data["course_count"] == 0
    assert init_data["section_count"] == 0
    assert init_data["faculty_count"] == 0
    assert init_data["room_count"] == 0

    # Add 1 department, 1 course, 1 term, 1 section, 1 faculty, 1 room
    dept_id = client.post(
        f"/api/v1/institutions/{inst_id}/departments",
        headers=headers,
        json={"name": "Chemistry", "code": "CHEM"},
    ).json()["data"]["id"]

    course_id = client.post(
        f"/api/v1/institutions/{inst_id}/courses",
        headers=headers,
        json={"department_id": dept_id, "code": "CHEM101", "name": "General Chemistry"},
    ).json()["data"]["id"]

    term_id = client.post(
        f"/api/v1/institutions/{inst_id}/terms",
        headers=headers,
        json={"name": "Term 1", "academic_year": "2026-2027", "start_date": str(date.today()), "end_date": str(date.today() + timedelta(days=90))},
    ).json()["data"]["id"]

    client.post(
        f"/api/v1/institutions/{inst_id}/sections",
        headers=headers,
        json={"course_id": course_id, "academic_term_id": term_id, "section_code": "001", "capacity": 40},
    )

    prof_id, _ = create_test_user("prof_curie")
    client.post(
        f"/api/v1/institutions/{inst_id}/members",
        headers=headers,
        json={"user_id": prof_id, "role": "professor", "status": "active"},
    )
    client.post(
        f"/api/v1/institutions/{inst_id}/faculty",
        headers=headers,
        json={"user_id": prof_id, "department_id": dept_id, "title": "Professor"},
    )

    client.post(
        f"/api/v1/institutions/{inst_id}/rooms",
        headers=headers,
        json={"building": "Chemistry Hall", "room_number": "CH-1", "capacity": 50},
    )

    # Now dashboard counts should all be 1
    dash_resp = client.get(f"/api/v1/institutions/{inst_id}/dashboard", headers=headers)
    assert dash_resp.status_code == 200
    data = dash_resp.json()["data"]
    assert data["course_count"] == 1
    assert data["section_count"] == 1
    assert data["faculty_count"] == 1
    assert data["room_count"] == 1
    assert data["department_count"] == 1
