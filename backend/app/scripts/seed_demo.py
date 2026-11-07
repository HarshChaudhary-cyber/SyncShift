"""
Repeatable, idempotent demo database seeding script for SyncShift.

Features:
- Restricted to local/test/development environments (strictly refuses execution in production).
- Idempotent: re-running updates or skips existing seed-owned records without duplication.
- CLI seed targets a separate, initially empty local demo database.
- Verification support (--verify): verifies authentications against the seeded database.
- Writes credentials to local excluded file and prints manual test table.
"""

import os
import sys
import argparse
import json
import hashlib
import secrets
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


DEMO_PASSWORDS = {key: secrets.token_urlsafe(18) + "A1!" for key in (
    "admin", "professor", "student_primary", "student_unrelated",
    "beacon_student", "beacon_admin", "default_user",
)}

DEMO_DOMAINS = ["@ssdemo.example", "@riverdemo.example"]
DEMO_INSTITUTION_CODES = ["SSDEMO", "RIVERDEMO"]
SEED_DATE = datetime.now(ZoneInfo("Europe/London")).date()
CREDENTIALS_PATH = Path(BACKEND_DIR) / ".demo-credentials.json"
MANIFEST_PATH = Path(BACKEND_DIR) / ".demo-manifest.json"


def demo_database_path() -> Path:
    verify_not_production()
    if not settings.DATABASE_URL.startswith("sqlite:///"):
        raise RuntimeError("Use a dedicated local SQLite demo database")
    db_path = Path(engine.url.database).resolve()
    if db_path.name != "syncshift-demo.db":
        raise RuntimeError("Refusing to seed another database; set DATABASE_URL to sqlite:///./syncshift-demo.db")
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
    except Exception:
        raise RuntimeError("Demo schema migration failed; inspect the database before seeding")


def reset_demo_data(db):
    """
    Remove seed-owned demo records deterministically without dropping tables
    or touching non-demo user data.
    """
    if not getattr(db, "_seed_reset_authorized", False):
        raise RuntimeError("Reset requires the isolated database manifest and unchanged database")
    verify_not_production()
    print("[*] Resetting demo-owned records...")

    # 1. Identify demo institutions
    demo_insts = db.query(Institution).filter(Institution.code.in_(DEMO_INSTITUTION_CODES)).all()
    demo_inst_ids = [inst.id for inst in demo_insts]

    # 2. Identify demo users
    demo_users = db.query(User).filter(
        (User.email.like("%@ssdemo.example")) | (User.email.like("%@riverdemo.example"))
    ).all()
    demo_user_ids = [u.id for u in demo_users]

    if demo_user_ids:
        # Delete user-dependent records
        db.query(TimeBlock).filter(TimeBlock.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(StudyTask).filter(StudyTask.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(NotificationLog).filter(NotificationLog.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(UserPreference).filter(UserPreference.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(ClassMember).filter(ClassMember.user_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(ClassAnnouncement).filter(ClassAnnouncement.author_id.in_(demo_user_ids)).delete(synchronize_session=False)
        db.query(SectionEnrollment).filter(SectionEnrollment.student_id.in_(demo_user_ids)).delete(synchronize_session=False)

    if demo_inst_ids:
        # Delete class workspaces linked to demo institutions
        demo_workspaces = db.query(ClassWorkspace).filter(ClassWorkspace.institution_id.in_(demo_inst_ids)).all()
        ws_ids = [ws.id for ws in demo_workspaces]
        if ws_ids:
            db.query(ClassEvent).filter(ClassEvent.class_id.in_(ws_ids)).delete(synchronize_session=False)
            db.query(ClassAnnouncement).filter(ClassAnnouncement.class_id.in_(ws_ids)).delete(synchronize_session=False)
            db.query(ClassMember).filter(ClassMember.class_id.in_(ws_ids)).delete(synchronize_session=False)
            db.query(ClassWorkspace).filter(ClassWorkspace.id.in_(ws_ids)).delete(synchronize_session=False)

        # Delete meetings, timetables, sections, courses, rooms, terms, depts
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
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
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
        # Existing accounts and manual edits are never changed by a repeated seed.
        return user
    return user


def seed_demo_data(db) -> Dict[str, Any]:
    """Populate primary and secondary institutions and connected entities."""
    verify_not_production()
    apply_migrations()

    print("[*] Starting idempotent seeding of SyncShift demo dataset...")

    # ──────────────────────────────────────────────────────────────────────────
    # 1. PRIMARY UNIVERSITY: SyncShift Demo University
    # ──────────────────────────────────────────────────────────────────────────
    inst_apex = db.query(Institution).filter_by(code="SSDEMO").first()
    if not inst_apex:
        inst_apex = Institution(
            name="SyncShift Demo University",
            code="SSDEMO",
            description="Premier research and technology university in London.",
            country="United Kingdom",
            timezone="Europe/London",
            email_domain="ssdemo.example",
            is_active=True,
        )
        db.add(inst_apex)
        db.commit()
        db.refresh(inst_apex)

    # 3 Departments
    depts_data = [
        ("Department of Computer Science & Engineering", "CS", "Software systems, AI, and cybersecurity."),
        ("Department of Mathematics & Data Science", "MATH", "Pure/applied mathematics, statistics, and optimization."),
        ("Department of Electrical & Electronic Engineering", "EE", "Circuits, embedded systems, and robotics."),
    ]
    dept_map = {}
    for name, code, desc in depts_data:
        dept = db.query(Department).filter_by(institution_id=inst_apex.id, code=code).first()
        if not dept:
            dept = Department(institution_id=inst_apex.id, name=name, code=code, description=desc, is_active=True)
            db.add(dept)
            db.commit()
            db.refresh(dept)
        dept_map[code] = dept

    # Academic term spans the configured seed date and the following weeks.
    today = SEED_DATE
    term_name = f"Demo Term {today.year}"
    term = db.query(AcademicTerm).filter_by(institution_id=inst_apex.id, name=term_name).first()
    if not term:
        term = AcademicTerm(
            institution_id=inst_apex.id,
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
        room = db.query(Room).filter_by(institution_id=inst_apex.id, building=bldg, room_number=num).first()
        if not room:
            room = Room(
                institution_id=inst_apex.id,
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
        c = db.query(AcademicCourse).filter_by(institution_id=inst_apex.id, code=code).first()
        if not c:
            c = AcademicCourse(
                institution_id=inst_apex.id,
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
                institution_id=inst_apex.id,
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

    # 4 Professors
    prof_data = [
        ("professor.asha@ssdemo.example", "Dr. Asha Rao", DEMO_PASSWORDS["professor"], "CS", "FAC-CS-001", "Professor of Computer Science"),
        ("prof.lovelace@ssdemo.example", "Dr. Ada Lovelace", DEMO_PASSWORDS["default_user"], "CS", "FAC-CS-002", "Associate Professor of Computing"),
        ("prof.gauss@ssdemo.example", "Dr. Carl Friedrich Gauss", DEMO_PASSWORDS["default_user"], "MATH", "FAC-MATH-001", "Professor of Mathematics"),
        ("prof.faraday@ssdemo.example", "Dr. Michael Faraday", DEMO_PASSWORDS["default_user"], "EE", "FAC-EE-001", "Senior Lecturer in Electrical Engineering"),
    ]
    prof_map = {}
    for email, dname, pw, dcode, ecode, title in prof_data:
        u = get_or_create_user(db, email, dname, pw)
        mem = db.query(InstitutionMembership).filter_by(institution_id=inst_apex.id, user_id=u.id).first()
        if not mem:
            mem = InstitutionMembership(institution_id=inst_apex.id, user_id=u.id, role="professor", status="active")
            db.add(mem)
        else:
            mem.role = "professor"
            mem.status = "active"
            mem.deleted_at = None

        prof_prof = db.query(FacultyProfile).filter_by(institution_id=inst_apex.id, user_id=u.id).first()
        if not prof_prof:
            prof_prof = FacultyProfile(
                institution_id=inst_apex.id,
                user_id=u.id,
                department_id=dept_map[dcode].id,
                employee_code=ecode,
                title=title,
                status="active",
            )
            db.add(prof_prof)
        db.commit()
        db.refresh(prof_prof)
        prof_map[email] = (u, prof_prof)

    # 1 University Super-Admin
    admin_apex = get_or_create_user(
        db, "admin@ssdemo.example", "Dr. Eleanor Vance", DEMO_PASSWORDS["admin"]
    )
    admin_mem = db.query(InstitutionMembership).filter_by(institution_id=inst_apex.id, user_id=admin_apex.id).first()
    if not admin_mem:
        admin_mem = InstitutionMembership(institution_id=inst_apex.id, user_id=admin_apex.id, role="super_admin", status="active")
        db.add(admin_mem)
    else:
        admin_mem.role = "super_admin"
        admin_mem.status = "active"
        admin_mem.deleted_at = None
    db.commit()

    # Assign Professors to Sections
    # Primary Professor (Dr. Turing) teaches at least two sections: CS101-SEC-A and CS201-SEC-A
    section_assignments = [
        ("CS101-SEC-A", "professor.asha@ssdemo.example", True),
        ("CS201-SEC-A", "professor.asha@ssdemo.example", True),
        ("CS301-SEC-A", "prof.lovelace@ssdemo.example", True),
        ("MATH101-SEC-A", "prof.gauss@ssdemo.example", True),
        ("MATH201-SEC-A", "prof.gauss@ssdemo.example", True),
        ("EE101-SEC-A", "prof.faraday@ssdemo.example", True),
    ]
    for scode, p_email, is_prim in section_assignments:
        _, fp = prof_map[p_email]
        sec = section_map[scode]
        assign = db.query(SectionFacultyAssignment).filter_by(section_id=sec.id, faculty_id=fp.id).first()
        if not assign:
            assign = SectionFacultyAssignment(
                institution_id=inst_apex.id,
                section_id=sec.id,
                faculty_id=fp.id,
                role="instructor",
                is_primary=is_prim,
            )
            db.add(assign)
    db.commit()

    # 12 Students with institution-scoped enrollment numbers (strings with leading zeros preserved)
    students_info = [
        # (email, display_name, password, enrollment_number, program, dept_code)
        ("student.arjun@ssdemo.example", "Arjun Mehta", DEMO_PASSWORDS["student_primary"], "00041001", "B.Sc. Computer Science", "CS"),
        ("student.meera@ssdemo.example", "Meera Shah", DEMO_PASSWORDS["student_unrelated"], "00041002", "B.Eng. Electrical Engineering", "EE"),
        ("student.sophia@ssdemo.example", "Sophia Chen", DEMO_PASSWORDS["default_user"], "00103", "B.Sc. Computer Science", "CS"),
        ("student.noah@ssdemo.example", "Noah Patel", DEMO_PASSWORDS["default_user"], "00104", "B.Sc. Computer Science", "CS"),
        ("student.emma@ssdemo.example", "Emma Watson", DEMO_PASSWORDS["default_user"], "00105", "B.Sc. Mathematics & Computing", "MATH"),
        ("student.lucas@ssdemo.example", "Lucas Kim", DEMO_PASSWORDS["default_user"], "00106", "B.Sc. Mathematics & Computing", "MATH"),
        ("student.olivia@ssdemo.example", "Olivia Garcia", DEMO_PASSWORDS["default_user"], "00107", "B.Sc. Computer Science", "CS"),
        ("student.ethan@ssdemo.example", "Ethan Brown", DEMO_PASSWORDS["default_user"], "00108", "B.Eng. Electrical Engineering", "EE"),
        ("student.ava@ssdemo.example", "Ava Martinez", DEMO_PASSWORDS["default_user"], "00109", "B.Sc. Computer Science", "CS"),
        ("student.oliver@ssdemo.example", "Oliver Wilson", DEMO_PASSWORDS["default_user"], "00110", "B.Sc. Mathematics & Computing", "MATH"),
        ("student.isabella@ssdemo.example", "Isabella Taylor", DEMO_PASSWORDS["default_user"], "00111", "B.Eng. Electrical Engineering", "EE"),
        ("student.mason@ssdemo.example", "Mason Anderson", DEMO_PASSWORDS["default_user"], "00112", "B.Sc. Computer Science", "CS"),
    ]
    student_map = {}
    for email, dname, pw, snum, prog, dcode in students_info:
        u = get_or_create_user(db, email, dname, pw)
        mem = db.query(InstitutionMembership).filter_by(institution_id=inst_apex.id, user_id=u.id).first()
        if not mem:
            mem = InstitutionMembership(institution_id=inst_apex.id, user_id=u.id, role="student", status="active")
            db.add(mem)
        else:
            mem.role = "student"
            mem.status = "active"
            mem.deleted_at = None

        sp = db.query(StudentProfile).filter_by(institution_id=inst_apex.id, user_id=u.id).first()
        if not sp:
            sp = StudentProfile(
                institution_id=inst_apex.id,
                user_id=u.id,
                department_id=dept_map[dcode].id,
                student_number=snum,
                program=prog,
                year_of_study=2,
                status="active",
            )
            db.add(sp)
        else:
            sp.student_number = snum
            sp.program = prog
            sp.status = "active"
            sp.deleted_at = None
        db.commit()
        db.refresh(sp)
        student_map[email] = (u, sp)

    # Enroll Students:
    # 1. Primary Student (Arjun Mehta): Enrolled in Dr. Turing's sections (CS101-SEC-A, CS201-SEC-A) and MATH101-SEC-A
    # 2. Unrelated Student (Meera Shah): Enrolled strictly in EE101-SEC-A (NOT in Dr. Turing's sections)
    # 3. Other students enrolled across sections
    enrollment_matrix = [
        ("student.arjun@ssdemo.example", ["CS101-SEC-A", "CS201-SEC-A", "MATH101-SEC-A"]),
        ("student.meera@ssdemo.example", ["EE101-SEC-A"]),
        ("student.sophia@ssdemo.example", ["CS101-SEC-A", "CS201-SEC-A", "CS301-SEC-A"]),
        ("student.noah@ssdemo.example", ["CS101-SEC-A", "CS301-SEC-A", "MATH201-SEC-A"]),
        ("student.emma@ssdemo.example", ["MATH101-SEC-A", "MATH201-SEC-A", "CS101-SEC-A"]),
        ("student.lucas@ssdemo.example", ["MATH101-SEC-A", "MATH201-SEC-A"]),
        ("student.olivia@ssdemo.example", ["CS101-SEC-A", "CS201-SEC-A"]),
        ("student.ethan@ssdemo.example", ["EE101-SEC-A"]),
        ("student.ava@ssdemo.example", ["CS101-SEC-A", "MATH101-SEC-A"]),
        ("student.oliver@ssdemo.example", ["MATH101-SEC-A", "MATH201-SEC-A"]),
        ("student.isabella@ssdemo.example", ["EE101-SEC-A"]),
        ("student.mason@ssdemo.example", ["CS201-SEC-A", "CS301-SEC-A"]),
    ]
    for s_email, sec_codes in enrollment_matrix:
        u, sp = student_map[s_email]
        for scode in sec_codes:
            sec = section_map[scode]
            enr = db.query(SectionEnrollment).filter_by(section_id=sec.id, student_id=u.id).first()
            if not enr:
                enr = SectionEnrollment(
                    institution_id=inst_apex.id,
                    student_id=u.id,
                    student_profile_id=sp.id,
                    section_id=sec.id,
                    status="active",
                )
                db.add(enr)
    db.commit()

    # Published timetable and supported draft, both tied to the configured term.
    tt_active_name = f"Demo {today.year} Master Timetable"
    tt_active = db.query(Timetable).filter_by(institution_id=inst_apex.id, name=tt_active_name).first()
    if not tt_active:
        tt_active = Timetable(
            institution_id=inst_apex.id,
            academic_term_id=term.id,
            name=tt_active_name,
            status="active",
            description=f"Official published university schedule for {term_name}.",
        )
        db.add(tt_active)
        db.commit()
        db.refresh(tt_active)

    # Draft Timetable for Spring exploratory scenarios
    tt_draft_name = f"Demo {today.year} Draft Timetable"
    tt_draft = db.query(Timetable).filter_by(institution_id=inst_apex.id, name=tt_draft_name).first()
    if not tt_draft:
        tt_draft = Timetable(
            institution_id=inst_apex.id,
            academic_term_id=term.id,
            name=tt_draft_name,
            status="draft",
            description="Draft timetable for upcoming curriculum planning and room scheduling.",
        )
        db.add(tt_draft)
        db.commit()
        db.refresh(tt_draft)

    # Scheduled Course Meetings across weekdays (Day of week: 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat)
    # Covering today (Saturday, Oct 3, 2026 -> day 6) and upcoming weekdays (Mon-Fri)
    # Day mapping in CourseMeeting: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
    meetings_data = [
        # Monday (day 1)
        ("CS101-SEC-A", 1, time(9, 0), time(10, 30), "Alan Turing Building:LH-101", "professor.asha@ssdemo.example", "lecture"),
        ("MATH101-SEC-A", 1, time(11, 0), time(12, 30), "Mathematics Wing:CR-105", "prof.gauss@ssdemo.example", "lecture"),
        ("CS201-SEC-A", 1, time(14, 0), time(15, 30), "Grace Hopper Complex:LAB-201", "professor.asha@ssdemo.example", "laboratory"),
        # Tuesday (day 2)
        ("CS301-SEC-A", 2, time(10, 0), time(11, 30), "Ada Lovelace Tower:SEM-301", "prof.lovelace@ssdemo.example", "lecture"),
        ("EE101-SEC-A", 2, time(13, 0), time(15, 0), "Engineering Pavilion:LAB-104", "prof.faraday@ssdemo.example", "laboratory"),
        # Wednesday (day 3)
        ("CS101-SEC-A", 3, time(9, 0), time(10, 30), "Alan Turing Building:LH-101", "professor.asha@ssdemo.example", "lecture"),
        ("CS201-SEC-A", 3, time(11, 0), time(12, 30), "Grace Hopper Complex:LAB-201", "professor.asha@ssdemo.example", "lecture"),
        ("MATH201-SEC-A", 3, time(14, 0), time(15, 30), "Mathematics Wing:CR-105", "prof.gauss@ssdemo.example", "lecture"),
        # Thursday (day 4)
        ("CS301-SEC-A", 4, time(10, 0), time(11, 30), "Grace Hopper Complex:LAB-201", "prof.lovelace@ssdemo.example", "laboratory"),
        ("MATH101-SEC-A", 4, time(13, 0), time(14, 30), "Mathematics Wing:CR-105", "prof.gauss@ssdemo.example", "lecture"),
        # Friday (day 5)
        ("CS101-SEC-A", 5, time(10, 0), time(11, 30), "Alan Turing Building:LH-101", "professor.asha@ssdemo.example", "tutorial"),
        ("EE101-SEC-A", 5, time(13, 0), time(14, 30), "Claude Shannon Building:LH-102", "prof.faraday@ssdemo.example", "lecture"),
        # Saturday (day 6 - Today, Oct 3, 2026)
        ("CS201-SEC-A", 6, time(10, 0), time(11, 30), "Alan Turing Building:LH-101", "professor.asha@ssdemo.example", "lecture"),
    ]
    for scode, dow, st, et, rkey, p_email, mtype in meetings_data:
        sec = section_map[scode]
        rm = room_map[rkey]
        _, fp = prof_map[p_email]
        mtg = db.query(CourseMeeting).filter_by(
            timetable_id=tt_active.id,
            section_id=sec.id,
            day_of_week=dow,
            start_time=st,
        ).first()
        if not mtg:
            mtg = CourseMeeting(
                institution_id=inst_apex.id,
                timetable_id=tt_active.id,
                section_id=sec.id,
                academic_term_id=term.id,
                day_of_week=dow,
                start_time=st,
                end_time=et,
                room_id=rm.id,
                faculty_id=fp.id,
                meeting_type=mtype,
                status="active",
            )
            db.add(mtg)
    db.commit()

    # Synchronize ClassWorkspaces for all Sections
    ensure_legacy_workspaces(db)

    # Add Shared Class Events for CS101-SEC-A (Taught by Dr. Turing)
    cs101_sec = section_map["CS101-SEC-A"]
    cs101_ws = db.query(ClassWorkspace).filter_by(section_id=cs101_sec.id).first()
    if cs101_ws:
        # 1. Published special workshop event today
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

        # 2. Published guest lecture next Tuesday (2026-10-06)
        evt_next = db.query(ClassEvent).filter_by(class_id=cs101_ws.id, title="Industry Guest Lecture: High-Scale Distributed Systems").first()
        if not evt_next:
            evt_next = ClassEvent(
                class_id=cs101_ws.id,
                title="Industry Guest Lecture: High-Scale Distributed Systems",
                location="Turing Lecture Hall (LH-101)",
                event_date=SEED_DATE + timedelta(days=2),
                start_time="16:00",
                end_time="17:30",
                status="published",
            )
            db.add(evt_next)

        # 3. Draft review session event (not yet published by Dr. Turing)
        evt_draft = db.query(ClassEvent).filter_by(class_id=cs101_ws.id, title="Midterm Review & Q&A Session").first()
        if not evt_draft:
            evt_draft = ClassEvent(
                class_id=cs101_ws.id,
                title="Midterm Review & Q&A Session",
                location="Turing Lecture Hall (LH-101)",
                event_date=SEED_DATE + timedelta(days=5),
                start_time="15:00",
                end_time="16:30",
                status="draft",
            )
            db.add(evt_draft)
        db.commit()

    # Personal Tasks & Personal Planner Blocks for Primary Student (Arjun Mehta)
    maya_user, _ = student_map["student.arjun@ssdemo.example"]
    tasks_maya = [
        ("Implement Red-Black Tree in C++", 6.0, SEED_DATE + timedelta(days=4), TaskStatus.PENDING, "high"),
        ("Database Normalization Problem Set 2", 4.0, SEED_DATE + timedelta(days=7), TaskStatus.PENDING, "medium"),
        ("Linear Algebra Eigenvector Practice", 3.0, SEED_DATE + timedelta(days=1), TaskStatus.DONE, "medium"),
    ]
    for title, hrs, deadline, tstatus, priority in tasks_maya:
        task = db.query(StudyTask).filter_by(user_id=maya_user.id, title=title).first()
        if not task:
            task = StudyTask(
                user_id=maya_user.id,
                title=title,
                total_hours_required=hrs,
                deadline=deadline,
                status=tstatus,
                priority=priority,
            )
            db.add(task)
    db.commit()

    # Maya's Personal Routine and Part-time Work Shift TimeBlocks
    # 1. Part-time campus tutoring shift (Tuesdays and Thursdays)
    shift_tue = db.query(TimeBlock).filter_by(user_id=maya_user.id, title="Campus Library Student Assistant").first()
    if not shift_tue:
        shift_tue = TimeBlock(
            user_id=maya_user.id,
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
        db.add(shift_tue)

    # 2. Personal gym/fitness routine
    gym_block = db.query(TimeBlock).filter_by(user_id=maya_user.id, title="Evening Fitness & Gym Routine").first()
    if not gym_block:
        gym_block = TimeBlock(
            user_id=maya_user.id,
            type=BlockType.STUDY,
            status=BlockStatus.ENROLLED,
            title="Evening Fitness & Gym Routine",
            location="Apex Sports Centre",
            is_recurring=True,
            recurrence_interval=1,
            day_of_week=1,  # Monday
            start_time=time(17, 0),
            end_time=time(18, 30),
            duration_minutes=90,
            is_flexible=True,
        )
        db.add(gym_block)
    db.commit()

    # Personal Tasks & Private Planner Blocks for Primary Professor (Dr. Turing)
    turing_user, _ = prof_map["professor.asha@ssdemo.example"]
    tasks_turing = [
        ("Finalize Midterm Exam Questions & Solutions", 5.0, SEED_DATE + timedelta(days=6), TaskStatus.PENDING, "high"),
        ("Review Graduate Research Proposals", 8.0, SEED_DATE + timedelta(days=11), TaskStatus.PENDING, "medium"),
        ("Grade Assignment 1 Coding Submissions", 6.0, SEED_DATE - timedelta(days=2), TaskStatus.DONE, "high"),
    ]
    for title, hrs, deadline, tstatus, priority in tasks_turing:
        task = db.query(StudyTask).filter_by(user_id=turing_user.id, title=title).first()
        if not task:
            task = StudyTask(
                user_id=turing_user.id,
                title=title,
                total_hours_required=hrs,
                deadline=deadline,
                status=tstatus,
                priority=priority,
            )
            db.add(task)

    # Private Appointments for Dr. Turing (students cannot see)
    priv_app = db.query(TimeBlock).filter_by(user_id=turing_user.id, title="Doctor Appointment (Private)").first()
    if not priv_app:
        priv_app = TimeBlock(
            user_id=turing_user.id,
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
        db.add(priv_app)
    db.commit()

    # Notifications for Maya and Dr. Turing
    notifs = [
        (maya_user.id, "TIMETABLE_UPDATE", "Official Timetable Published", "Your Autumn 2026 timetable has been published and synced.", True),
        (maya_user.id, "CLASS_UPDATE", "CS101 Workshop Scheduled", "Dr. Asha Rao announced the Complexity Theory Workshop.", False),
        (turing_user.id, "TIMETABLE_UPDATE", "Teaching Schedule Activated", "You are assigned as primary instructor for CS101 and CS201.", True),
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

    # User Preferences
    for u in [maya_user, turing_user, admin_apex]:
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

    # ──────────────────────────────────────────────────────────────────────────
    # 2. SECOND UNIVERSITY: Riverside Demo University (for tenant isolation)
    # ──────────────────────────────────────────────────────────────────────────
    inst_beacon = db.query(Institution).filter_by(code="RIVERDEMO").first()
    if not inst_beacon:
        inst_beacon = Institution(
            name="Riverside Demo University",
            code="RIVERDEMO",
            description="Autonomous technical state university.",
            country="United Kingdom",
            timezone="Europe/London",
            email_domain="riverdemo.example",
            is_active=True,
        )
        db.add(inst_beacon)
        db.commit()
        db.refresh(inst_beacon)

    dept_beacon = db.query(Department).filter_by(institution_id=inst_beacon.id, code="CS").first()
    if not dept_beacon:
        dept_beacon = Department(
            institution_id=inst_beacon.id,
            name="Department of Computing Sciences",
            code="CS",
            description="Computing and software engineering.",
            is_active=True,
        )
        db.add(dept_beacon)
        db.commit()
        db.refresh(dept_beacon)

    # Beacon Super Admin
    admin_beacon = get_or_create_user(
        db, "admin@riverdemo.example", "Dr. Raymond Holt", DEMO_PASSWORDS["beacon_admin"]
    )
    b_admin_mem = db.query(InstitutionMembership).filter_by(institution_id=inst_beacon.id, user_id=admin_beacon.id).first()
    if not b_admin_mem:
        b_admin_mem = InstitutionMembership(institution_id=inst_beacon.id, user_id=admin_beacon.id, role="super_admin", status="active")
        db.add(b_admin_mem)
    else:
        b_admin_mem.role = "super_admin"
        b_admin_mem.status = "active"
        b_admin_mem.deleted_at = None
    db.commit()

    # Beacon Student with IDENTICAL ENROLLMENT NUMBER "00041001" as Arjun Mehta
    beacon_student = get_or_create_user(
        db, "student.kabir@riverdemo.example", "Kabir Khan", DEMO_PASSWORDS["beacon_student"]
    )
    b_stud_mem = db.query(InstitutionMembership).filter_by(institution_id=inst_beacon.id, user_id=beacon_student.id).first()
    if not b_stud_mem:
        b_stud_mem = InstitutionMembership(institution_id=inst_beacon.id, user_id=beacon_student.id, role="student", status="active")
        db.add(b_stud_mem)
    else:
        b_stud_mem.role = "student"
        b_stud_mem.status = "active"
        b_stud_mem.deleted_at = None

    b_sp = db.query(StudentProfile).filter_by(institution_id=inst_beacon.id, user_id=beacon_student.id).first()
    if not b_sp:
        b_sp = StudentProfile(
            institution_id=inst_beacon.id,
            user_id=beacon_student.id,
            department_id=dept_beacon.id,
            student_number="00041001",  # Exactly the same enrollment number as Arjun Mehta!
            program="B.Sc. Computing",
            year_of_study=1,
            status="active",
        )
        db.add(b_sp)
    else:
        b_sp.student_number = "00041001"
        b_sp.status = "active"
        b_sp.deleted_at = None
    db.commit()

    print("[+] Demo dataset successfully seeded.")

    # Prepare credentials metadata
    credentials = {
        "metadata": {
            "environment": "Local demo only",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "primary_university": {
                "name": inst_apex.name,
                "code": inst_apex.code,
                "id": inst_apex.id,
            },
            "secondary_university": {
                "name": inst_beacon.name,
                "code": inst_beacon.code,
                "id": inst_beacon.id,
            },
        },
        "accounts": [
            {
                "role": "Super Admin",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_apex.id,
                "email": "admin@ssdemo.example",
                "display_name": "Dr. Eleanor Vance",
                "enrollment_number": None,
                "password": DEMO_PASSWORDS["admin"],
                "notes": "Full administrative privileges over Apex Institute.",
            },
            {
                "role": "Professor",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_apex.id,
                "email": "professor.asha@ssdemo.example",
                "display_name": "Dr. Asha Rao",
                "enrollment_number": None,
                "password": DEMO_PASSWORDS["professor"],
                "notes": "Teaches CS101-SEC-A and CS201-SEC-A.",
            },
            {
                "role": "Student (Primary)",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_apex.id,
                "email": "student.arjun@ssdemo.example",
                "display_name": "Arjun Mehta",
                "enrollment_number": "00041001",
                "password": DEMO_PASSWORDS["student_primary"],
                "notes": "Enrolled in Dr. Turing's sections.",
            },
            {
                "role": "Student (Unrelated)",
                "university": "SyncShift Demo University",
                "university_code": "SSDEMO",
                "institution_id": inst_apex.id,
                "email": "student.meera@ssdemo.example",
                "display_name": "Meera Shah",
                "enrollment_number": "00041002",
                "password": DEMO_PASSWORDS["student_unrelated"],
                "notes": "Enrolled only in EE101-SEC-A; cannot see Dr. Turing's classes.",
            },
            {
                "role": "Student (Cross-University)",
                "university": "Riverside Demo University",
                "university_code": "RIVERDEMO",
                "institution_id": inst_beacon.id,
                "email": "student.kabir@riverdemo.example",
                "display_name": "Kabir Khan",
                "enrollment_number": "00041001",
                "password": DEMO_PASSWORDS["beacon_student"],
                "notes": "Duplicate enrollment '00041001' in different university.",
            },
            {
                "role": "Super Admin (Beacon)",
                "university": "Riverside Demo University",
                "university_code": "RIVERDEMO",
                "institution_id": inst_beacon.id,
                "email": "admin@riverdemo.example",
                "display_name": "Dr. Raymond Holt",
                "enrollment_number": None,
                "password": DEMO_PASSWORDS["beacon_admin"],
                "notes": "Admin for Riverside Demo University.",
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
        user = db.query(User).filter_by(email=email).first()
        if not user:
            print(f"[-] FAILED: User {email} not found in DB.")
            all_ok = False
            continue

        if not verify_password(pw, user.password_hash):
            print(f"[-] FAILED: Password verification failed for {email}.")
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

        print(f"[+] Verified account: {acc['role']} ({email}) - OK")

    if all_ok:
        print("[+] All demo accounts successfully verified against database!")
    else:
        print("[-] One or more verifications failed.")
        sys.exit(1)


def print_credentials_table(creds: Dict[str, Any]):
    """Print the final required markdown table."""
    print("\n" + "=" * 90)
    print("DEMO CREDENTIALS TABLE (Local demo only)")
    print("=" * 90)
    print(f"{'Role':<22} | {'University':<30} | {'Email':<28} | {'Enrollment':<12} | {'Password'}")
    print("-" * 115)
    for acc in creds["accounts"]:
        snum = acc["enrollment_number"] or "-"
        print(f"{acc['role']:<22} | {acc['university']:<30} | {acc['email']:<28} | {snum:<12} | {acc['password']}")
    print("=" * 90 + "\n")


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

    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        if manifest.get("database") != str(db_path):
            raise RuntimeError("Demo manifest belongs to another database")
        if args.reset:
            if database_digest(db_path) != manifest["sha256"]:
                raise RuntimeError("Demo database has changed since seeding; preserve manual edits and reset manually after review")
        else:
            if not CREDENTIALS_PATH.exists():
                raise RuntimeError("Credentials missing; refusing to reseed or reset passwords")
            if args.verify:
                with SessionLocal() as verify_db:
                    verify_demo_dataset(verify_db, json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8")))
            print("Demo already seeded. Existing data and passwords preserved.")
            return
    elif args.reset:
        raise RuntimeError("No tracked demo seed exists for reset")
    elif db_path.exists() and db_path.stat().st_size:
        raise RuntimeError("Demo target is not empty or tracked; choose a fresh dedicated syncshift-demo.db")

    db = SessionLocal()
    try:
        if args.reset:
            db._seed_reset_authorized = True
            reset_demo_data(db)
            MANIFEST_PATH.unlink()
            CREDENTIALS_PATH.unlink(missing_ok=True)
            return

        creds = seed_demo_data(db)
        if args.verify:
            verify_demo_dataset(db, creds)
        CREDENTIALS_PATH.write_text(json.dumps(creds, indent=2), encoding="utf-8")
        MANIFEST_PATH.write_text(json.dumps({"database": str(db_path), "sha256": database_digest(db_path), "date": SEED_DATE.isoformat()}), encoding="utf-8")
        print(f"Demo credentials saved to {CREDENTIALS_PATH}; passwords are not printed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
