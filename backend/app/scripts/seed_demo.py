"""
Repeatable, idempotent demo database seeding script for SyncShift.

Features:
- Restricted to local/test/development environments (strictly refuses execution in production).
- Idempotent: re-running updates or skips existing seed-owned records without duplication.
- Seeds exactly five primary role-based demo accounts:
    1 Administrator: Eleanor Vance (admin.demo@ssdemo.example)
    2 Teachers:      Dr. Asha Rao (teacher.one@ssdemo.example), Dr. Daniel Carter (teacher.two@ssdemo.example)
    2 Students:      Arjun Mehta (student.one@ssdemo.example), Meera Shah (student.two@ssdemo.example)
- Removes outdated demo credentials and legacy demo accounts.
- CLI seed targets a dedicated local SQLite demo database.
- Verification support (--verify): verifies authentication and profiles against the seeded database.
- Writes credentials metadata to local excluded file and prints readable credentials table.
"""

import os
import sys
import argparse
import json
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, Any

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from alembic.config import Config
from alembic import command
from sqlalchemy import func

from app.config import settings
from app.database import SessionLocal, engine
from app.models.institution import Institution, InstitutionMembership
from app.models.department import Department
from app.models.academic_course import AcademicCourse
from app.models.academic_term import AcademicTerm
from app.models.room import Room
from app.models.academic_section import AcademicSection
from app.models.user import User
from app.models.faculty import FacultyProfile
from app.models.student_profile import StudentProfile
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.section_enrollment import SectionEnrollment
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.course_meeting import CourseMeeting
from app.models.class_workspace import ClassWorkspace, ClassMember, ClassEvent, ClassAnnouncement
from app.models.time_block import TimeBlock, BlockType, BlockStatus
from app.models.study_task import StudyTask, TaskStatus
from app.models.notification import NotificationLog
from app.models.user_preference import UserPreference
from app.routers.auth import hash_password, verify_password
from app.services.class_workspaces import ensure_legacy_workspaces

# Fixed demo credentials for synthetic local testing only
DEMO_PASSWORDS = {
    "admin": "SyncAdmin2026!",
    "teacher_one": "SyncTeacher1!2026",
    "teacher_two": "SyncTeacher2!2026",
    "student_one": "SyncStudent1!2026",
    "student_two": "SyncStudent2!2026",
}

PRIMARY_DEMO_EMAILS = {
    "admin.demo@ssdemo.example",
    "teacher.one@ssdemo.example",
    "teacher.two@ssdemo.example",
    "student.one@ssdemo.example",
    "student.two@ssdemo.example",
}

OLD_DEMO_EMAILS = [
    "admin@ssdemo.example",
    "professor.asha@ssdemo.example",
    "prof.lovelace@ssdemo.example",
    "prof.gauss@ssdemo.example",
    "prof.faraday@ssdemo.example",
    "student.arjun@ssdemo.example",
    "student.meera@ssdemo.example",
    "student.sophia@ssdemo.example",
    "student.noah@ssdemo.example",
    "student.emma@ssdemo.example",
    "student.lucas@ssdemo.example",
    "student.olivia@ssdemo.example",
    "student.ethan@ssdemo.example",
    "student.ava@ssdemo.example",
    "student.oliver@ssdemo.example",
    "student.isabella@ssdemo.example",
    "student.mason@ssdemo.example",
    "admin@riverdemo.example",
    "student.kabir@riverdemo.example",
]

DEMO_DOMAINS = ["@ssdemo.example"]
DEMO_INSTITUTION_CODES = ["SSDEMO"]
SEED_DATE = datetime.now(ZoneInfo("Europe/London")).date()
CREDENTIALS_PATH = Path(BACKEND_DIR) / ".demo-credentials.json"


def get_manifest_path(db_path: Path) -> Path:
    if db_path.name == "syncshift-demo.db":
        return Path(BACKEND_DIR) / ".demo-manifest.json"
    return Path(BACKEND_DIR) / f".{db_path.stem}-manifest.json"


def demo_database_path() -> Path:
    verify_not_production()
    if not settings.DATABASE_URL.startswith("sqlite:///"):
        raise RuntimeError("Use a dedicated local SQLite demo database")
    db_path = Path(engine.url.database).resolve()
    if not (db_path.name.endswith("-demo.db") or db_path.name.endswith("_demo.db")):
        raise RuntimeError(
            f"Refusing to seed non-demo database '{db_path.name}'. "
            "Set DATABASE_URL to a dedicated demo database (e.g. sqlite:///./syncshift-roles-demo.db or sqlite:///./syncshift-demo.db)"
        )
    return db_path


def database_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_not_production():
    """Safety guard: prevent running demo seed against a production environment."""
    env = (settings.ENV or "").lower().strip()
    if env in ("production", "prod", "live"):
        print(f"[-] ERROR: Seeding demo data is strictly prohibited in environment: '{env}'.")
        sys.exit(1)


def apply_migrations():
    """Apply any pending Alembic migrations before seeding."""
    print("[*] Checking and applying Alembic migrations to head...")
    try:
        alembic_ini_path = os.path.join(BACKEND_DIR, "alembic.ini")
        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")
        print("[+] Database schema is up to date.")
    except Exception as exc:
        raise RuntimeError(f"Demo schema migration failed: {exc}; inspect the database before seeding")


def cleanup_old_demo_accounts(db):
    """
    Remove outdated demo accounts and any legacy seeded users,
    ensuring exactly the five primary demo accounts remain.
    Preserves real user accounts and test accounts outside the demo domain.
    """
    old_users = db.query(User).filter(
        (User.email.in_(OLD_DEMO_EMAILS))
        | ((User.email.like("%@ssdemo.example") | User.email.like("%@riverdemo.example"))
           & ~User.email.in_(PRIMARY_DEMO_EMAILS))
    ).all()

    if not old_users:
        return

    old_user_ids = [u.id for u in old_users]
    print(f"[*] Removing {len(old_user_ids)} outdated demo account(s)...")

    db.query(TimeBlock).filter(TimeBlock.user_id.in_(old_user_ids)).delete(synchronize_session=False)
    db.query(StudyTask).filter(StudyTask.user_id.in_(old_user_ids)).delete(synchronize_session=False)
    db.query(NotificationLog).filter(NotificationLog.user_id.in_(old_user_ids)).delete(synchronize_session=False)
    db.query(UserPreference).filter(UserPreference.user_id.in_(old_user_ids)).delete(synchronize_session=False)
    db.query(ClassMember).filter(ClassMember.user_id.in_(old_user_ids)).delete(synchronize_session=False)
    db.query(ClassAnnouncement).filter(ClassAnnouncement.author_id.in_(old_user_ids)).delete(synchronize_session=False)
    db.query(SectionEnrollment).filter(SectionEnrollment.student_id.in_(old_user_ids)).delete(synchronize_session=False)

    old_faculty_ids = [f.id for f in db.query(FacultyProfile.id).filter(FacultyProfile.user_id.in_(old_user_ids)).all()]
    if old_faculty_ids:
        db.query(SectionFacultyAssignment).filter(SectionFacultyAssignment.faculty_id.in_(old_faculty_ids)).delete(synchronize_session=False)
        db.query(CourseMeeting).filter(CourseMeeting.faculty_id.in_(old_faculty_ids)).delete(synchronize_session=False)

    db.query(FacultyProfile).filter(FacultyProfile.user_id.in_(old_user_ids)).delete(synchronize_session=False)
    db.query(StudentProfile).filter(StudentProfile.user_id.in_(old_user_ids)).delete(synchronize_session=False)
    db.query(InstitutionMembership).filter(InstitutionMembership.user_id.in_(old_user_ids)).delete(synchronize_session=False)

    for u in old_users:
        db.delete(u)

    db.commit()
    print("[+] Outdated demo accounts removed.")


def reset_demo_data(db):
    """
    Remove seed-owned demo records deterministically without dropping tables
    or touching non-demo user data.
    """
    if not getattr(db, "_seed_reset_authorized", False):
        raise RuntimeError("Reset requires the isolated database manifest and unchanged database")
    verify_not_production()
    print("[*] Resetting demo-owned records...")

    # Identify demo institutions
    demo_insts = db.query(Institution).filter(Institution.code.in_(["SSDEMO", "RIVERDEMO"])).all()
    demo_inst_ids = [inst.id for inst in demo_insts]

    # Identify demo users
    demo_users = db.query(User).filter(
        (User.email.like("%@ssdemo.example")) | (User.email.like("%@riverdemo.example"))
    ).all()
    demo_user_ids = [u.id for u in demo_users]

    if demo_user_ids:
        db.query(TimeBlock).filter(TimeBlock.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(StudyTask).filter(StudyTask.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(NotificationLog).filter(NotificationLog.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(UserPreference).filter(UserPreference.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(ClassMember).filter(ClassMember.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(ClassAnnouncement).filter(ClassAnnouncement.author_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(SectionEnrollment).filter(SectionEnrollment.student_id.in_(demo_user_ids)).delete(synchronize_session=False)

    if demo_inst_ids:
        demo_workspaces = db.query(ClassWorkspace).filter(ClassWorkspace.institution_id.in_(demo_inst_ids)).all()
        ws_ids = [ws.id for ws in demo_workspaces]
        if ws_ids:
            db.query(ClassEvent).filter(ClassEvent.class_id.in_(ws_ids)).delete(synchronize_session=False)
            db.query(ClassAnnouncement).filter(ClassAnnouncement.class_id.in_(ws_ids)).delete(synchronize_session=False)
            db.query(ClassMember).filter(ClassMember.class_id.in_(ws_ids)).delete(synchronize_session=False)
            db.query(ClassWorkspace).filter(ClassWorkspace.id.in_(ws_ids)).delete(synchronize_session=False)

        db.query(CourseMeeting).filter(CourseMeeting.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(TimetableVersion).filter(TimetableVersion.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(Timetable).filter(Timetable.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(SectionFacultyAssignment).filter(SectionFacultyAssignment.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(SectionEnrollment).filter(SectionEnrollment.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(AcademicSection).filter(AcademicSection.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(AcademicCourse).filter(AcademicCourse.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(Room).filter(Room.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(AcademicTerm).filter(AcademicTerm.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(FacultyProfile).filter(FacultyProfile.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(StudentProfile).filter(StudentProfile.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(Department).filter(Department.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(InstitutionMembership).filter(InstitutionMembership.institution_id.in_(demo_inst_ids)).delete(synchronize_session=False)
        db.query(Institution).filter(Institution.id.in_(demo_inst_ids)).delete(synchronize_session=False)

    if demo_users:
        for u in demo_users:
            db.delete(u)

    db.commit()
    print("[+] Successfully cleared all demo-owned records while preserving non-demo data.")


def get_or_create_user(db, email: str, display_name: str, password_plain: str, timezone_name="Europe/London") -> User:
    """
    Ensure the demo user exists with the exact fixed demo password and active status.
    Updates password hash and display name on repeated runs.
    """
    email_clean = email.strip().lower()
    user = db.query(User).filter(func.lower(User.email) == email_clean).first()
    if not user:
        user = User(
            email=email_clean,
            display_name=display_name,
            name=display_name,
            password_hash=hash_password(password_plain),
            timezone=timezone_name,
            weekly_work_hour_limit=20.0,
            theme="dark",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.display_name = display_name
        user.name = display_name
        user.timezone = timezone_name
        user.deleted_at = None
        # Always verify/update to the fixed demo password
        if not user.password_hash or not verify_password(password_plain, user.password_hash):
            user.password_hash = hash_password(password_plain)
        db.commit()
        db.refresh(user)
    return user


def seed_demo_data(db) -> Dict[str, Any]:
    """
    Populate SyncShift Demo University (SSDEMO) and exactly five primary demo accounts:
    1 Administrator: Eleanor Vance
    2 Teachers:      Dr. Asha Rao, Dr. Daniel Carter
    2 Students:      Arjun Mehta, Meera Shah
    """
    verify_not_production()
    apply_migrations()

    print("[*] Starting idempotent seeding of SyncShift role-based demo dataset...")

    # Clean up any outdated demo accounts
    cleanup_old_demo_accounts(db)

    # ──────────────────────────────────────────────────────────────────────────
    # 1. PRIMARY UNIVERSITY: SyncShift Demo University (SSDEMO)
    # ──────────────────────────────────────────────────────────────────────────
    inst_demo = db.query(Institution).filter_by(code="SSDEMO").first()
    if not inst_demo:
        inst_demo = Institution(
            name="SyncShift Demo University",
            code="SSDEMO",
            description="Premier research and technology university in London.",
            country="United Kingdom",
            timezone="Europe/London",
            email_domain="ssdemo.example",
            is_active=True,
        )
        db.add(inst_demo)
        db.commit()
        db.refresh(inst_demo)
    else:
        inst_demo.name = "SyncShift Demo University"
        inst_demo.description = "Premier research and technology university in London."
        inst_demo.is_active = True
        db.commit()

    # 3 Departments
    depts_data = [
        ("Department of Computer Science & Engineering", "CS", "Software systems, AI, and cybersecurity."),
        ("Department of Mathematics & Data Science", "MATH", "Pure/applied mathematics, statistics, and optimization."),
        ("Department of Electrical & Electronic Engineering", "EE", "Circuits, embedded systems, and robotics."),
    ]
    dept_map = {}
    for name, code, desc in depts_data:
        dept = db.query(Department).filter_by(institution_id=inst_demo.id, code=code).first()
        if not dept:
            dept = Department(institution_id=inst_demo.id, name=name, code=code, description=desc, is_active=True)
            db.add(dept)
            db.commit()
            db.refresh(dept)
        dept_map[code] = dept

    # Academic term
    today = SEED_DATE
    term_name = f"Demo Term {today.year}"
    term = db.query(AcademicTerm).filter_by(institution_id=inst_demo.id, name=term_name).first()
    if not term:
        term = AcademicTerm(
            institution_id=inst_demo.id,
            name=term_name,
            academic_year=f"{today.year}-{today.year + 1}",
            term_type="semester",
            start_date=today - timedelta(days=14),
            end_date=today + timedelta(days=120),
            status="active",
        )
        db.add(term)
        db.commit()
        db.refresh(term)

    # 6 Rooms with capacities
    rooms_data = [
        ("Alan Turing Building", "LH-101", "Turing Lecture Hall", 120, "lecture_hall", "Laser Projector, Dual Microphones, Recording Camera"),
        ("Grace Hopper Complex", "LAB-201", "Hopper Systems Lab", 35, "laboratory", "35 High-Performance Linux Workstations, Dual Displays"),
        ("Ada Lovelace Tower", "SEM-301", "Lovelace Seminar Suite", 30, "seminar_room", "Interactive Display, Audio Baffles"),
        ("Claude Shannon Building", "LH-102", "Shannon Auditorium", 80, "lecture_hall", "Tiered Seating, High-Fidelity Audio"),
        ("Mathematics Wing", "CR-105", "Gauss Colloquium Room", 45, "classroom", "Triple Sliding Chalkboards, Document Camera"),
        ("Engineering Pavilion", "LAB-104", "Faraday Embedded Lab", 25, "laboratory", "Oscilloscopes, Soldering Stations, Bench Power Supplies"),
    ]
    room_map = {}
    for bldg, num, rname, cap, rtype, feats in rooms_data:
        room = db.query(Room).filter_by(institution_id=inst_demo.id, building=bldg, room_number=num).first()
        if not room:
            room = Room(
                institution_id=inst_demo.id,
                building=bldg,
                room_number=num,
                name=rname,
                capacity=cap,
                room_type=rtype,
                basic_features=feats,
                status="active",
            )
            db.add(room)
            db.commit()
            db.refresh(room)
        room_map[f"{bldg}:{num}"] = room

    # 8 Subjects / Academic Courses
    courses_data = [
        ("CS101", "Algorithms & Data Structures", dept_map["CS"].id, 4, "undergraduate", 40, "lecture_hall", "Fundamental algorithms, complexity, graph traversals, and dynamic programming."),
        ("CS201", "Database Systems & Architecture", dept_map["CS"].id, 4, "undergraduate", 35, "classroom", "Relational models, SQL, transactions, ACID properties, and indexing."),
        ("CS301", "Operating Systems & Concurrency", dept_map["CS"].id, 4, "undergraduate", 30, "laboratory", "Process synchronization, virtual memory, scheduling, and file systems."),
        ("CS401", "Distributed Systems & Cloud", dept_map["CS"].id, 3, "undergraduate", 30, "lecture_hall", "Consensus algorithms, replication, microservices, and fault tolerance."),
        ("MATH101", "Linear Algebra & Calculus", dept_map["MATH"].id, 4, "undergraduate", 45, "classroom", "Vector spaces, eigenvalues, matrix decompositions, and multivariable limits."),
        ("MATH201", "Probability & Discrete Mathematics", dept_map["MATH"].id, 3, "undergraduate", 40, "classroom", "Combinatorics, graph theory, random variables, and expectation."),
        ("EE101", "Digital Logic & Circuit Design", dept_map["EE"].id, 4, "undergraduate", 25, "laboratory", "Boolean algebra, combinational circuits, flip-flops, and sequential state machines."),
        ("EE201", "Embedded Microcontrollers", dept_map["EE"].id, 3, "undergraduate", 25, "laboratory", "ARM microcontrollers, interrupts, PWM, ADC, and hardware interfacing."),
    ]
    course_map = {}
    for code, cname, did, credits, level, mrc, rtype, desc in courses_data:
        c = db.query(AcademicCourse).filter_by(institution_id=inst_demo.id, code=code).first()
        if not c:
            c = AcademicCourse(
                institution_id=inst_demo.id,
                department_id=did,
                code=code,
                name=cname,
                description=desc,
                credits=credits,
                level=level,
                status="active",
                min_room_capacity=mrc,
                required_room_type=rtype,
            )
            db.add(c)
            db.commit()
            db.refresh(c)
        course_map[code] = c

    # 6 Class Sections
    sections_data = [
        ("CS101", "CS101-SEC-A", 40, "Section A: Core lecture and programming exercises."),
        ("CS201", "CS201-SEC-A", 35, "Section A: Theory and SQL lab assignments."),
        ("CS301", "CS301-SEC-A", 30, "Section A: Systems architecture and kernel labs."),
        ("MATH101", "MATH101-SEC-A", 45, "Section A: Applied mathematical foundations."),
        ("MATH201", "MATH201-SEC-A", 40, "Section A: Discrete models and probability."),
        ("EE101", "EE101-SEC-A", 25, "Section A: Digital systems and breadboard prototyping."),
    ]
    section_map = {}
    for ccode, scode, cap, sdesc in sections_data:
        sec = db.query(AcademicSection).filter_by(
            course_id=course_map[ccode].id,
            academic_term_id=term.id,
            section_code=scode,
        ).first()
        if not sec:
            sec = AcademicSection(
                institution_id=inst_demo.id,
                course_id=course_map[ccode].id,
                academic_term_id=term.id,
                section_code=scode,
                capacity=cap,
                status="active",
                description=sdesc,
            )
            db.add(sec)
            db.commit()
            db.refresh(sec)
        section_map[scode] = sec

    # ──────────────────────────────────────────────────────────────────────────
    # 2. DEMO ACCOUNT 1: University Administrator (Eleanor Vance)
    # ──────────────────────────────────────────────────────────────────────────
    admin_user = get_or_create_user(
        db,
        email="admin.demo@ssdemo.example",
        display_name="Eleanor Vance",
        password_plain=DEMO_PASSWORDS["admin"],
    )
    admin_mem = db.query(InstitutionMembership).filter_by(institution_id=inst_demo.id, user_id=admin_user.id).first()
    if not admin_mem:
        admin_mem = InstitutionMembership(
            institution_id=inst_demo.id,
            user_id=admin_user.id,
            role="super_admin",
            status="active",
        )
        db.add(admin_mem)
    else:
        admin_mem.role = "super_admin"
        admin_mem.status = "active"
        admin_mem.deleted_at = None
    db.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 3. DEMO ACCOUNTS 2 & 3: Teachers (Dr. Asha Rao & Dr. Daniel Carter)
    # ──────────────────────────────────────────────────────────────────────────
    # Teacher 1: Dr. Asha Rao (CS Department)
    t1_user = get_or_create_user(
        db,
        email="teacher.one@ssdemo.example",
        display_name="Dr. Asha Rao",
        password_plain=DEMO_PASSWORDS["teacher_one"],
    )
    t1_mem = db.query(InstitutionMembership).filter_by(institution_id=inst_demo.id, user_id=t1_user.id).first()
    if not t1_mem:
        t1_mem = InstitutionMembership(
            institution_id=inst_demo.id,
            user_id=t1_user.id,
            role="professor",
            status="active",
        )
        db.add(t1_mem)
    else:
        t1_mem.role = "professor"
        t1_mem.status = "active"
        t1_mem.deleted_at = None

    t1_fp = db.query(FacultyProfile).filter_by(institution_id=inst_demo.id, user_id=t1_user.id).first()
    if not t1_fp:
        t1_fp = FacultyProfile(
            institution_id=inst_demo.id,
            user_id=t1_user.id,
            department_id=dept_map["CS"].id,
            employee_code="FAC-CS-001",
            title="Professor of Computer Science",
            status="active",
        )
        db.add(t1_fp)
    else:
        t1_fp.department_id = dept_map["CS"].id
        t1_fp.employee_code = "FAC-CS-001"
        t1_fp.title = "Professor of Computer Science"
        t1_fp.status = "active"
        t1_fp.deleted_at = None
    db.commit()
    db.refresh(t1_fp)

    # Teacher 2: Dr. Daniel Carter (Mathematics Department)
    t2_user = get_or_create_user(
        db,
        email="teacher.two@ssdemo.example",
        display_name="Dr. Daniel Carter",
        password_plain=DEMO_PASSWORDS["teacher_two"],
    )
    t2_mem = db.query(InstitutionMembership).filter_by(institution_id=inst_demo.id, user_id=t2_user.id).first()
    if not t2_mem:
        t2_mem = InstitutionMembership(
            institution_id=inst_demo.id,
            user_id=t2_user.id,
            role="professor",
            status="active",
        )
        db.add(t2_mem)
    else:
        t2_mem.role = "professor"
        t2_mem.status = "active"
        t2_mem.deleted_at = None

    t2_fp = db.query(FacultyProfile).filter_by(institution_id=inst_demo.id, user_id=t2_user.id).first()
    if not t2_fp:
        t2_fp = FacultyProfile(
            institution_id=inst_demo.id,
            user_id=t2_user.id,
            department_id=dept_map["MATH"].id,
            employee_code="FAC-MATH-001",
            title="Associate Professor of Mathematics",
            status="active",
        )
        db.add(t2_fp)
    else:
        t2_fp.department_id = dept_map["MATH"].id
        t2_fp.employee_code = "FAC-MATH-001"
        t2_fp.title = "Associate Professor of Mathematics"
        t2_fp.status = "active"
        t2_fp.deleted_at = None
    db.commit()
    db.refresh(t2_fp)

    # Assign Teachers to Sections:
    # Teacher 1 (Dr. Asha Rao): CS101-SEC-A and CS201-SEC-A
    # Teacher 2 (Dr. Daniel Carter): MATH101-SEC-A, MATH201-SEC-A, CS301-SEC-A, EE101-SEC-A
    section_assignments = [
        ("CS101-SEC-A", t1_fp.id, True),
        ("CS201-SEC-A", t1_fp.id, True),
        ("MATH101-SEC-A", t2_fp.id, True),
        ("MATH201-SEC-A", t2_fp.id, True),
        ("CS301-SEC-A", t2_fp.id, True),
        ("EE101-SEC-A", t2_fp.id, True),
    ]
    for scode, fp_id, is_prim in section_assignments:
        sec = section_map[scode]
        assign = db.query(SectionFacultyAssignment).filter_by(section_id=sec.id, faculty_id=fp_id).first()
        if not assign:
            assign = SectionFacultyAssignment(
                institution_id=inst_demo.id,
                section_id=sec.id,
                faculty_id=fp_id,
                role="instructor",
                is_primary=is_prim,
            )
            db.add(assign)
    db.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 4. DEMO ACCOUNTS 4 & 5: Students (Arjun Mehta & Meera Shah)
    # ──────────────────────────────────────────────────────────────────────────
    # Student 1: Arjun Mehta (CS Department, enrollment 00041001)
    s1_user = get_or_create_user(
        db,
        email="student.one@ssdemo.example",
        display_name="Arjun Mehta",
        password_plain=DEMO_PASSWORDS["student_one"],
    )
    s1_mem = db.query(InstitutionMembership).filter_by(institution_id=inst_demo.id, user_id=s1_user.id).first()
    if not s1_mem:
        s1_mem = InstitutionMembership(
            institution_id=inst_demo.id,
            user_id=s1_user.id,
            role="student",
            status="active",
        )
        db.add(s1_mem)
    else:
        s1_mem.role = "student"
        s1_mem.status = "active"
        s1_mem.deleted_at = None

    s1_sp = db.query(StudentProfile).filter_by(institution_id=inst_demo.id, user_id=s1_user.id).first()
    if not s1_sp:
        s1_sp = StudentProfile(
            institution_id=inst_demo.id,
            user_id=s1_user.id,
            department_id=dept_map["CS"].id,
            student_number="00041001",
            program="B.Sc. Computer Science",
            year_of_study=2,
            status="active",
        )
        db.add(s1_sp)
    else:
        s1_sp.department_id = dept_map["CS"].id
        s1_sp.student_number = "00041001"
        s1_sp.program = "B.Sc. Computer Science"
        s1_sp.status = "active"
        s1_sp.deleted_at = None
    db.commit()
    db.refresh(s1_sp)

    # Student 2: Meera Shah (Mathematics & Computing, enrollment 00041002)
    s2_user = get_or_create_user(
        db,
        email="student.two@ssdemo.example",
        display_name="Meera Shah",
        password_plain=DEMO_PASSWORDS["student_two"],
    )
    s2_mem = db.query(InstitutionMembership).filter_by(institution_id=inst_demo.id, user_id=s2_user.id).first()
    if not s2_mem:
        s2_mem = InstitutionMembership(
            institution_id=inst_demo.id,
            user_id=s2_user.id,
            role="student",
            status="active",
        )
        db.add(s2_mem)
    else:
        s2_mem.role = "student"
        s2_mem.status = "active"
        s2_mem.deleted_at = None

    s2_sp = db.query(StudentProfile).filter_by(institution_id=inst_demo.id, user_id=s2_user.id).first()
    if not s2_sp:
        s2_sp = StudentProfile(
            institution_id=inst_demo.id,
            user_id=s2_user.id,
            department_id=dept_map["MATH"].id,
            student_number="00041002",
            program="B.Sc. Mathematics & Computing",
            year_of_study=2,
            status="active",
        )
        db.add(s2_sp)
    else:
        s2_sp.department_id = dept_map["MATH"].id
        s2_sp.student_number = "00041002"
        s2_sp.program = "B.Sc. Mathematics & Computing"
        s2_sp.status = "active"
        s2_sp.deleted_at = None
    db.commit()
    db.refresh(s2_sp)

    # Enrollments:
    # Student 1: CS101-SEC-A, CS201-SEC-A, MATH101-SEC-A
    # Student 2: MATH101-SEC-A, MATH201-SEC-A, CS301-SEC-A
    student_enrollments = [
        (s1_user.id, s1_sp.id, ["CS101-SEC-A", "CS201-SEC-A", "MATH101-SEC-A"]),
        (s2_user.id, s2_sp.id, ["MATH101-SEC-A", "MATH201-SEC-A", "CS301-SEC-A"]),
    ]
    for uid, sp_id, sec_codes in student_enrollments:
        for scode in sec_codes:
            sec = section_map[scode]
            enr = db.query(SectionEnrollment).filter_by(section_id=sec.id, student_id=uid).first()
            if not enr:
                enr = SectionEnrollment(
                    institution_id=inst_demo.id,
                    student_id=uid,
                    student_profile_id=sp_id,
                    section_id=sec.id,
                    status="active",
                )
                db.add(enr)
    db.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 5. TIMETABLES & COURSE MEETINGS
    # ──────────────────────────────────────────────────────────────────────────
    tt_active_name = f"Demo {today.year} Master Timetable"
    tt_active = db.query(Timetable).filter_by(institution_id=inst_demo.id, name=tt_active_name).first()
    if not tt_active:
        tt_active = Timetable(
            institution_id=inst_demo.id,
            academic_term_id=term.id,
            name=tt_active_name,
            status="active",
            description=f"Official published university schedule for {term_name}.",
        )
        db.add(tt_active)
        db.commit()
        db.refresh(tt_active)

    tt_draft_name = f"Demo {today.year} Draft Timetable"
    tt_draft = db.query(Timetable).filter_by(institution_id=inst_demo.id, name=tt_draft_name).first()
    if not tt_draft:
        tt_draft = Timetable(
            institution_id=inst_demo.id,
            academic_term_id=term.id,
            name=tt_draft_name,
            status="draft",
            description="Draft timetable for upcoming curriculum planning and room scheduling.",
        )
        db.add(tt_draft)
        db.commit()
        db.refresh(tt_draft)

    # Course meetings (0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat)
    # Teacher 1 (Dr. Asha Rao) teaches CS101 and CS201
    # Teacher 2 (Dr. Daniel Carter) teaches MATH101, CS301, MATH201, EE101
    meetings_data = [
        # Monday (day 1)
        ("CS101-SEC-A", 1, time(9, 0), time(10, 30), "Alan Turing Building:LH-101", t1_fp.id, "lecture"),
        ("MATH101-SEC-A", 1, time(11, 0), time(12, 30), "Mathematics Wing:CR-105", t2_fp.id, "lecture"),
        ("CS201-SEC-A", 1, time(14, 0), time(15, 30), "Grace Hopper Complex:LAB-201", t1_fp.id, "laboratory"),
        # Tuesday (day 2)
        ("CS301-SEC-A", 2, time(10, 0), time(11, 30), "Ada Lovelace Tower:SEM-301", t2_fp.id, "lecture"),
        ("EE101-SEC-A", 2, time(13, 0), time(15, 0), "Engineering Pavilion:LAB-104", t2_fp.id, "laboratory"),
        # Wednesday (day 3)
        ("CS101-SEC-A", 3, time(9, 0), time(10, 30), "Alan Turing Building:LH-101", t1_fp.id, "lecture"),
        ("CS201-SEC-A", 3, time(11, 0), time(12, 30), "Grace Hopper Complex:LAB-201", t1_fp.id, "lecture"),
        ("MATH201-SEC-A", 3, time(14, 0), time(15, 30), "Mathematics Wing:CR-105", t2_fp.id, "lecture"),
        # Thursday (day 4)
        ("CS301-SEC-A", 4, time(10, 0), time(11, 30), "Grace Hopper Complex:LAB-201", t2_fp.id, "laboratory"),
        ("MATH101-SEC-A", 4, time(13, 0), time(14, 30), "Mathematics Wing:CR-105", t2_fp.id, "lecture"),
        # Friday (day 5)
        ("CS101-SEC-A", 5, time(10, 0), time(11, 30), "Alan Turing Building:LH-101", t1_fp.id, "tutorial"),
        ("EE101-SEC-A", 5, time(13, 0), time(14, 30), "Claude Shannon Building:LH-102", t2_fp.id, "lecture"),
        # Saturday (day 6)
        ("CS201-SEC-A", 6, time(10, 0), time(11, 30), "Alan Turing Building:LH-101", t1_fp.id, "lecture"),
    ]
    for scode, dow, st, et, rkey, fp_id, mtype in meetings_data:
        sec = section_map[scode]
        rm = room_map[rkey]
        mtg = db.query(CourseMeeting).filter_by(
            timetable_id=tt_active.id,
            section_id=sec.id,
            day_of_week=dow,
            start_time=st,
        ).first()
        if not mtg:
            mtg = CourseMeeting(
                institution_id=inst_demo.id,
                timetable_id=tt_active.id,
                section_id=sec.id,
                academic_term_id=term.id,
                day_of_week=dow,
                start_time=st,
                end_time=et,
                room_id=rm.id,
                faculty_id=fp_id,
                meeting_type=mtype,
                status="active",
            )
            db.add(mtg)
        else:
            mtg.faculty_id = fp_id
            mtg.room_id = rm.id
    db.commit()

    # Synchronize ClassWorkspaces for all Sections
    ensure_legacy_workspaces(db)

    # Class workspace events for CS101 (Teacher 1)
    cs101_sec = section_map["CS101-SEC-A"]
    cs101_ws = db.query(ClassWorkspace).filter_by(section_id=cs101_sec.id).first()
    if cs101_ws:
        evt_today = db.query(ClassEvent).filter_by(class_id=cs101_ws.id, title="Algorithm Complexity & Sorting Workshop").first()
        if not evt_today:
            evt_today = ClassEvent(
                class_id=cs101_ws.id,
                title="Algorithm Complexity & Sorting Workshop",
                location="Turing Lecture Hall (LH-101)",
                event_date=today,
                start_time="14:00",
                end_time="15:30",
                status="published",
            )
            db.add(evt_today)

        evt_next = db.query(ClassEvent).filter_by(class_id=cs101_ws.id, title="Industry Guest Lecture: Distributed Computing").first()
        if not evt_next:
            evt_next = ClassEvent(
                class_id=cs101_ws.id,
                title="Industry Guest Lecture: Distributed Computing",
                location="Turing Lecture Hall (LH-101)",
                event_date=SEED_DATE + timedelta(days=2),
                start_time="16:00",
                end_time="17:30",
                status="published",
            )
            db.add(evt_next)
        db.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 6. STUDENT PERSONAL SCHEDULES & DATA ISOLATION
    # ──────────────────────────────────────────────────────────────────────────
    # Student 1 (Arjun Mehta): Personal Tasks, Shifts, and Blocks
    tasks_s1 = [
        ("Implement Red-Black Tree in C++", 6.0, SEED_DATE + timedelta(days=4), TaskStatus.PENDING, "high"),
        ("Database Normalization Problem Set 2", 4.0, SEED_DATE + timedelta(days=7), TaskStatus.PENDING, "medium"),
        ("Linear Algebra Eigenvector Practice", 3.0, SEED_DATE + timedelta(days=1), TaskStatus.DONE, "medium"),
    ]
    for title, hrs, deadline, tstatus, priority in tasks_s1:
        task = db.query(StudyTask).filter_by(user_id=s1_user.id, title=title).first()
        if not task:
            task = StudyTask(
                user_id=s1_user.id,
                title=title,
                total_hours_required=hrs,
                deadline=deadline,
                status=tstatus,
                priority=priority,
            )
            db.add(task)
    db.commit()

    # Student 1: Part-time library work shift (Tuesday and Thursday)
    shift_s1 = db.query(TimeBlock).filter_by(user_id=s1_user.id, title="Campus Library Student Assistant").first()
    if not shift_s1:
        shift_s1 = TimeBlock(
            user_id=s1_user.id,
            type=BlockType.SHIFT,
            status=BlockStatus.ENROLLED,
            title="Campus Library Student Assistant",
            location="University Central Library, Level 2",
            is_recurring=True,
            recurrence_interval=1,
            day_of_week=2,  # Tuesday
            start_time=time(16, 0),
            end_time=time(19, 0),
            duration_minutes=180,
            hourly_wage=15.50,
            is_flexible=False,
        )
        db.add(shift_s1)

    # Student 1: Personal gym block (Monday)
    gym_s1 = db.query(TimeBlock).filter_by(user_id=s1_user.id, title="Evening Fitness & Gym Routine").first()
    if not gym_s1:
        gym_s1 = TimeBlock(
            user_id=s1_user.id,
            type=BlockType.STUDY,
            status=BlockStatus.ENROLLED,
            title="Evening Fitness & Gym Routine",
            location="Sports Centre",
            is_recurring=True,
            recurrence_interval=1,
            day_of_week=1,  # Monday
            start_time=time(17, 0),
            end_time=time(18, 30),
            duration_minutes=90,
            is_flexible=True,
        )
        db.add(gym_s1)
    db.commit()

    # Student 2 (Meera Shah): Personal Tasks, Shifts, and Blocks (Distinct from Student 1)
    tasks_s2 = [
        ("Discrete Probability Problem Set", 5.0, SEED_DATE + timedelta(days=5), TaskStatus.PENDING, "high"),
        ("Operating Systems Kernel Threading Lab", 8.0, SEED_DATE + timedelta(days=10), TaskStatus.PENDING, "high"),
    ]
    for title, hrs, deadline, tstatus, priority in tasks_s2:
        task = db.query(StudyTask).filter_by(user_id=s2_user.id, title=title).first()
        if not task:
            task = StudyTask(
                user_id=s2_user.id,
                title=title,
                total_hours_required=hrs,
                deadline=deadline,
                status=tstatus,
                priority=priority,
            )
            db.add(task)
    db.commit()

    # Student 2: Peer tutoring center shift (Wednesday and Friday)
    shift_s2 = db.query(TimeBlock).filter_by(user_id=s2_user.id, title="Peer Tutoring Center Shift").first()
    if not shift_s2:
        shift_s2 = TimeBlock(
            user_id=s2_user.id,
            type=BlockType.SHIFT,
            status=BlockStatus.ENROLLED,
            title="Peer Tutoring Center Shift",
            location="Mathematics Learning Center",
            is_recurring=True,
            recurrence_interval=1,
            day_of_week=3,  # Wednesday
            start_time=time(16, 0),
            end_time=time(18, 30),
            duration_minutes=150,
            hourly_wage=16.00,
            is_flexible=False,
        )
        db.add(shift_s2)

    # Student 2: Morning swim practice (Tuesday)
    swim_s2 = db.query(TimeBlock).filter_by(user_id=s2_user.id, title="Morning Swim Practice").first()
    if not swim_s2:
        swim_s2 = TimeBlock(
            user_id=s2_user.id,
            type=BlockType.STUDY,
            status=BlockStatus.ENROLLED,
            title="Morning Swim Practice",
            location="University Aquatics Center",
            is_recurring=True,
            recurrence_interval=1,
            day_of_week=2,  # Tuesday
            start_time=time(7, 30),
            end_time=time(8, 45),
            duration_minutes=75,
            is_flexible=True,
        )
        db.add(swim_s2)
    db.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 7. TEACHERS' PRIVATE PREPARATION TASKS & BLOCKS
    # ──────────────────────────────────────────────────────────────────────────
    # Teacher 1 (Dr. Asha Rao)
    tasks_t1 = [
        ("Finalize Midterm Exam Questions & Solutions", 5.0, SEED_DATE + timedelta(days=6), TaskStatus.PENDING, "high"),
        ("Review Graduate Research Proposals", 8.0, SEED_DATE + timedelta(days=11), TaskStatus.PENDING, "medium"),
        ("Grade Assignment 1 Coding Submissions", 6.0, SEED_DATE - timedelta(days=2), TaskStatus.DONE, "high"),
    ]
    for title, hrs, deadline, tstatus, priority in tasks_t1:
        task = db.query(StudyTask).filter_by(user_id=t1_user.id, title=title).first()
        if not task:
            task = StudyTask(
                user_id=t1_user.id,
                title=title,
                total_hours_required=hrs,
                deadline=deadline,
                status=tstatus,
                priority=priority,
            )
            db.add(task)

    priv_app_t1 = db.query(TimeBlock).filter_by(user_id=t1_user.id, title="Doctor Appointment (Private)").first()
    if not priv_app_t1:
        priv_app_t1 = TimeBlock(
            user_id=t1_user.id,
            type=BlockType.STUDY,
            status=BlockStatus.ENROLLED,
            title="Doctor Appointment (Private)",
            location="City Health Clinic",
            is_recurring=False,
            specific_date=SEED_DATE + timedelta(days=3),
            day_of_week=3,
            start_time=time(8, 0),
            end_time=time(9, 0),
            duration_minutes=60,
        )
        db.add(priv_app_t1)
    db.commit()

    # Teacher 2 (Dr. Daniel Carter)
    tasks_t2 = [
        ("Prepare Linear Algebra Lecture Notes", 4.0, SEED_DATE + timedelta(days=3), TaskStatus.PENDING, "high"),
        ("Set Discrete Mathematics Problem Sheet 3", 5.0, SEED_DATE + timedelta(days=8), TaskStatus.PENDING, "medium"),
    ]
    for title, hrs, deadline, tstatus, priority in tasks_t2:
        task = db.query(StudyTask).filter_by(user_id=t2_user.id, title=title).first()
        if not task:
            task = StudyTask(
                user_id=t2_user.id,
                title=title,
                total_hours_required=hrs,
                deadline=deadline,
                status=tstatus,
                priority=priority,
            )
            db.add(task)
    db.commit()

    # ──────────────────────────────────────────────────────────────────────────
    # 8. NOTIFICATIONS & PREFERENCES
    # ──────────────────────────────────────────────────────────────────────────
    notifs = [
        (s1_user.id, "TIMETABLE_UPDATE", "Official Timetable Published", "Your Autumn timetable has been published and synced.", True),
        (s1_user.id, "CLASS_UPDATE", "CS101 Workshop Scheduled", "Dr. Asha Rao scheduled the Complexity Theory Workshop.", False),
        (s2_user.id, "TIMETABLE_UPDATE", "Official Timetable Published", "Your Autumn timetable has been published and synced.", True),
        (t1_user.id, "TIMETABLE_UPDATE", "Teaching Schedule Activated", "You are assigned as primary instructor for CS101 and CS201.", True),
        (t2_user.id, "TIMETABLE_UPDATE", "Teaching Schedule Activated", "You are assigned as primary instructor for MATH101, MATH201, CS301, EE101.", True),
    ]
    for uid, ntype, title, body, is_read in notifs:
        n = db.query(NotificationLog).filter_by(user_id=uid, title=title).first()
        if not n:
            n = NotificationLog(
                user_id=uid,
                type=ntype,
                title=title,
                body=body,
                channel="in_app",
                delivery_status="delivered",
                read_at=datetime.now(timezone.utc) if is_read else None,
            )
            db.add(n)
    db.commit()

    # User preferences for all 5 demo users
    for u in [admin_user, t1_user, t2_user, s1_user, s2_user]:
        pref = db.query(UserPreference).filter_by(user_id=u.id).first()
        if not pref:
            pref = UserPreference(
                user_id=u.id,
                default_calendar_view="7day",
                planning_hours_start=8,
                planning_hours_end=19,
                reduced_motion="system",
            )
            db.add(pref)
    db.commit()

    print("[+] Demo dataset successfully seeded.")

    # Prepare credentials metadata
    credentials = {
        "metadata": {
            "environment": "Local demo only",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "primary_university": {
                "name": inst_demo.name,
                "code": inst_demo.code,
                "id": inst_demo.id,
            },
        },
        "accounts": [
            {
                "role": "University Administrator",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_demo.id,
                "email": "admin.demo@ssdemo.example",
                "display_name": "Eleanor Vance",
                "enrollment_number": None,
                "password": DEMO_PASSWORDS["admin"],
                "notes": "Full administrative privileges over SyncShift Demo University.",
            },
            {
                "role": "Teacher 1",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_demo.id,
                "email": "teacher.one@ssdemo.example",
                "display_name": "Dr. Asha Rao",
                "enrollment_number": None,
                "password": DEMO_PASSWORDS["teacher_one"],
                "notes": "Teaches CS101-SEC-A and CS201-SEC-A.",
            },
            {
                "role": "Teacher 2",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_demo.id,
                "email": "teacher.two@ssdemo.example",
                "display_name": "Dr. Daniel Carter",
                "enrollment_number": None,
                "password": DEMO_PASSWORDS["teacher_two"],
                "notes": "Teaches MATH101-SEC-A, MATH201-SEC-A, CS301-SEC-A, and EE101-SEC-A.",
            },
            {
                "role": "Student 1",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_demo.id,
                "email": "student.one@ssdemo.example",
                "display_name": "Arjun Mehta",
                "enrollment_number": "00041001",
                "password": DEMO_PASSWORDS["student_one"],
                "notes": "Enrolled in CS101-SEC-A, CS201-SEC-A, and MATH101-SEC-A with personal work shifts.",
            },
            {
                "role": "Student 2",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_demo.id,
                "email": "student.two@ssdemo.example",
                "display_name": "Meera Shah",
                "enrollment_number": "00041002",
                "password": DEMO_PASSWORDS["student_two"],
                "notes": "Enrolled in MATH101-SEC-A, MATH201-SEC-A, and CS301-SEC-A with separate tutoring shifts.",
            },
        ],
    }

    return credentials


def verify_demo_dataset(db, creds: Dict[str, Any]):
    """Verify that seeded accounts exist and can authenticate with both email and enrollment."""
    print("[*] Verifying seeded authentication accounts in the database...")
    all_ok = True
    for acc in creds["accounts"]:
        email = acc["email"]
        pw = acc["password"]
        user = db.query(User).filter(func.lower(User.email) == email.lower()).first()
        if not user:
            print(f"[-] FAILED: User {email} not found in DB.")
            all_ok = False
            continue

        if not verify_password(pw, user.password_hash):
            print(f"[-] FAILED: Password verification failed for {email}.")
            all_ok = False
            continue

        # Check membership
        mem = db.query(InstitutionMembership).filter_by(user_id=user.id, status="active", deleted_at=None).first()
        if not mem:
            print(f"[-] FAILED: Active membership missing for {email}.")
            all_ok = False
            continue

        # If student, verify enrollment lookup
        snum = acc.get("enrollment_number")
        if snum:
            sp = db.query(StudentProfile).filter_by(user_id=user.id, student_number=snum).first()
            if not sp:
                print(f"[-] FAILED: Student profile for {email} with number {snum} not found.")
                all_ok = False
                continue

        print(f"[+] Verified account: {acc['role']} ({email}) [role={mem.role}] - OK")

    if all_ok:
        print("[+] All 5 demo accounts successfully verified against database!")
    else:
        print("[-] One or more verifications failed.")
        sys.exit(1)


def print_credentials_table(creds: Dict[str, Any]):
    """Print the final required markdown table."""
    print("\n" + "=" * 105)
    print("DEMO LOGIN CREDENTIALS (SyncShift Demo University - SSDEMO)")
    print("=" * 105)
    print(f"{'Role':<26} | {'Name':<18} | {'Email':<30} | {'Password'}")
    print("-" * 105)
    for acc in creds["accounts"]:
        print(f"{acc['role']:<26} | {acc['display_name']:<18} | {acc['email']:<30} | {acc['password']}")
    print("=" * 105 + "\n")


def main():
    global SEED_DATE
    parser = argparse.ArgumentParser(description="SyncShift Repeatable Demo Seeding & Reset Utility")
    parser.add_argument("--reset", action="store_true", help="Remove seed-owned demo records without touching non-demo data")
    parser.add_argument("--verify", action="store_true", help="Verify seeded accounts authentication")
    parser.add_argument("--date", type=date.fromisoformat, help="University-local seed date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.date:
        SEED_DATE = args.date
    db_path = demo_database_path()
    manifest_file = get_manifest_path(db_path)

    if manifest_file.exists():
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if manifest.get("database") != str(db_path):
            raise RuntimeError(f"Demo manifest {manifest_file.name} belongs to another database ({manifest.get('database')})")
        if args.reset:
            if database_digest(db_path) != manifest["sha256"]:
                raise RuntimeError("Demo database has changed since seeding; preserve manual edits and reset manually after review")
        else:
            if not CREDENTIALS_PATH.exists():
                raise RuntimeError("Credentials missing; refusing to reseed or reset passwords")
            # If verify flag is passed, verify and exit
            if args.verify:
                with SessionLocal() as verify_db:
                    verify_demo_dataset(verify_db, json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8")))
            print("Demo already seeded. Existing data and passwords verified.")
            return
    elif args.reset:
        raise RuntimeError("No tracked demo seed exists for reset")
    elif db_path.exists() and db_path.stat().st_size:
        # Check if it has tables already; if it's untracked non-empty db, warn or fail unless it's a fresh migration
        print("[*] Target database exists and has data; applying seed updates idempotently...")

    db = SessionLocal()
    try:
        if args.reset:
            db._seed_reset_authorized = True
            reset_demo_data(db)
            manifest_file.unlink(missing_ok=True)
            CREDENTIALS_PATH.unlink(missing_ok=True)
            return

        creds = seed_demo_data(db)
        if args.verify:
            verify_demo_dataset(db, creds)
        CREDENTIALS_PATH.write_text(json.dumps(creds, indent=2), encoding="utf-8")
        manifest_data = {
            "database": str(db_path),
            "sha256": database_digest(db_path),
            "date": SEED_DATE.isoformat(),
        }
        manifest_file.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        print_credentials_table(creds)
        print(f"Demo credentials saved to {CREDENTIALS_PATH}.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
