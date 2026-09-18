"""
seed_demo_data.py — Canonical Demonstration & Portfolio Seed Script for SyncShift (Task N12).

Creates a complete, realistic, and fictional institutional ecosystem:
- University: Northbridge University (NBU)
- Departments: Computer Science, Information Technology, Business
- Academic Term: Fall 2026 (Active term: 2026-09-01 to 2026-12-15)
- Classrooms: B204 (Lecture Hall, Cap 60), C101 (Classroom, Cap 40), Lab-3 (Lab, Cap 30)
- Faculty: Dr. Sarah Jenkins, Prof. Alan Miller, Dr. Maya Patel
- Courses: CS301 (Computer Networks), CS302 (Database Systems), IT305 (Cyber Security), CS304 (Software Engineering)
- Sections: CS301-A, CS302-A, IT305-B, CS304-A
- Timetable & Published Version 1: Official schedule with scheduled course meetings
- Users & Personas:
    * Administrator: Dr. Robert Vance (admin@northbridge.edu / Northbridge2026!)
    * Faculty: Prof. Sarah Jenkins (faculty@northbridge.edu / Faculty2026!)
    * Faculty: Prof. Alan Miller (alan.miller@northbridge.edu / Faculty2026!)
    * Student: Alex Taylor (alex.taylor@student.northbridge.edu / Student2026!)
    * Student: Jordan Lee (jordan.lee@student.northbridge.edu / Student2026!)
- Enrollments: Alex (CS301-A, CS302-A); Jordan (CS301-A, IT305-B)
- Student Personal Life: Barista work shifts (Tue/Thu 17:00-21:00), study preferences, weekly limits
- Version 2 Draft: Ready for administrative impact preview, approval, and publication flow

Idempotent: Safe to run repeatedly.
"""

import sys
from datetime import date, datetime, time, timezone
import bcrypt

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from app.database import SessionLocal, init_db
from app.models.academic_course import AcademicCourse
from app.models.academic_section import AcademicSection
from app.models.academic_term import AcademicTerm
from app.models.course_meeting import CourseMeeting
from app.models.department import Department
from app.models.faculty import FacultyProfile
from app.models.institution import Institution, InstitutionMembership
from app.models.notification import NotificationLog, NotificationPrefs
from app.models.room import Room
from app.models.section_enrollment import SectionEnrollment
from app.models.section_faculty_assignment import SectionFacultyAssignment
from app.models.student_availability import StudentAvailability
from app.models.student_constraint import StudentConstraint, StudentPreference
from app.models.student_profile import StudentProfile
from app.models.study_task import StudyTask
from app.models.time_block import BlockStatus, BlockType, TimeBlock
from app.models.timetable import Timetable
from app.models.timetable_version import TimetableVersion
from app.models.user import User


def hash_pwd(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed():
    print("=" * 65)
    print("  SyncShift — Seeding Northbridge University Demo Ecosystem (N12)")
    print("=" * 65)

    init_db()
    db = SessionLocal()

    try:
        # 1. Institution
        inst = db.query(Institution).filter(Institution.code == "NBU").first()
        if not inst:
            inst = Institution(
                name="Northbridge University",
                code="NBU",
                country="GB",
                timezone="Europe/London",
                email_domain="northbridge.edu",
                description="Northbridge University is a forward-thinking institution for engineering and computing.",
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)
            print(f"✓ Created Institution: {inst.name} (ID: {inst.id})")
        else:
            print(f"• Institution already exists: {inst.name} (ID: {inst.id})")

        # 2. Departments
        depts_data = [
            ("Computer Science", "CS"),
            ("Information Technology", "IT"),
            ("Business & Management", "BUS"),
        ]
        dept_map = {}
        for name, code in depts_data:
            d = db.query(Department).filter(Department.institution_id == inst.id, Department.code == code).first()
            if not d:
                d = Department(institution_id=inst.id, name=name, code=code)
                db.add(d)
                db.commit()
                db.refresh(d)
                print(f"✓ Created Department: {name} ({code})")
            dept_map[code] = d

        # 3. Rooms
        rooms_data = [
            ("B204", "Science & Engineering Hall", "Lecture Hall B204", 60, "lecture_hall"),
            ("C101", "Computing Center", "Classroom C101", 40, "classroom"),
            ("Lab-3", "Turing Technology Wing", "Computer Lab 3", 30, "laboratory"),
        ]
        room_map = {}
        for r_num, bldg, name, cap, r_type in rooms_data:
            r = db.query(Room).filter(Room.institution_id == inst.id, Room.room_number == r_num).first()
            if not r:
                r = Room(
                    institution_id=inst.id,
                    room_number=r_num,
                    building=bldg,
                    name=name,
                    capacity=cap,
                    room_type=r_type,
                )
                db.add(r)
                db.commit()
                db.refresh(r)
                print(f"✓ Created Room: {r_num} (Cap: {cap})")
            room_map[r_num] = r

        # 4. Users (Admin + Students + Faculty)
        admin_user = db.query(User).filter(User.email == "admin@northbridge.edu").first()
        if not admin_user:
            admin_user = User(
                email="admin@northbridge.edu",
                name="Dr. Robert Vance",
                password_hash=hash_pwd("Northbridge2026!"),
                timezone="Europe/London",
                weekly_work_hour_limit=40.0,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print("✓ Created Admin User: admin@northbridge.edu")

        student_alex = db.query(User).filter(User.email == "alex.taylor@student.northbridge.edu").first()
        if not student_alex:
            student_alex = User(
                email="alex.taylor@student.northbridge.edu",
                name="Alex Taylor",
                password_hash=hash_pwd("Student2026!"),
                timezone="Europe/London",
                weekly_work_hour_limit=20.0,
                currency="GBP",
            )
            db.add(student_alex)
            db.commit()
            db.refresh(student_alex)
            print("✓ Created Student User: alex.taylor@student.northbridge.edu")

        student_jordan = db.query(User).filter(User.email == "jordan.lee@student.northbridge.edu").first()
        if not student_jordan:
            student_jordan = User(
                email="jordan.lee@student.northbridge.edu",
                name="Jordan Lee",
                password_hash=hash_pwd("Student2026!"),
                timezone="Europe/London",
                weekly_work_hour_limit=20.0,
                currency="GBP",
            )
            db.add(student_jordan)
            db.commit()
            db.refresh(student_jordan)
            print("✓ Created Student User: jordan.lee@student.northbridge.edu")

        # 5. Memberships
        for u, role in [(admin_user, "admin"), (student_alex, "student"), (student_jordan, "student")]:
            m = db.query(InstitutionMembership).filter(
                InstitutionMembership.institution_id == inst.id,
                InstitutionMembership.user_id == u.id,
            ).first()
            if not m:
                m = InstitutionMembership(
                    institution_id=inst.id,
                    user_id=u.id,
                    role=role,
                    status="active",
                )
                db.add(m)
                db.commit()

        # 6. Faculty Profiles
        faculty_data = [
            ("Prof. Sarah Jenkins", "faculty@northbridge.edu", dept_map["CS"].id, "Professor of Computer Science", "EMP-CS-00", "faculty"),
            ("Dr. Sarah Jenkins", "sarah.jenkins@northbridge.edu", dept_map["CS"].id, "Associate Professor", "EMP-CS-01", "professor"),
            ("Prof. Alan Miller", "alan.miller@northbridge.edu", dept_map["IT"].id, "Senior Lecturer", "EMP-IT-02", "professor"),
            ("Dr. Maya Patel", "maya.patel@northbridge.edu", dept_map["BUS"].id, "Assistant Professor", "EMP-BUS-03", "professor"),
        ]
        faculty_map = {}
        for fname, femail, fdept, ftitle, fcode, frole in faculty_data:
            fac_user = db.query(User).filter(User.email == femail).first()
            if not fac_user:
                fac_user = User(
                    email=femail,
                    name=fname,
                    password_hash=hash_pwd("Faculty2026!"),
                    timezone="Europe/London",
                )
                db.add(fac_user)
                db.commit()
                db.refresh(fac_user)

            fac_mem = db.query(InstitutionMembership).filter(
                InstitutionMembership.institution_id == inst.id,
                InstitutionMembership.user_id == fac_user.id,
            ).first()
            if not fac_mem:
                fac_mem = InstitutionMembership(
                    institution_id=inst.id,
                    user_id=fac_user.id,
                    role=frole,
                    status="active",
                )
                db.add(fac_mem)
                db.commit()

            fac = db.query(FacultyProfile).filter(
                FacultyProfile.institution_id == inst.id,
                FacultyProfile.user_id == fac_user.id,
            ).first()
            if not fac:
                fac = FacultyProfile(
                    institution_id=inst.id,
                    user_id=fac_user.id,
                    department_id=fdept,
                    title=ftitle,
                    employee_code=fcode,
                    status="active",
                )
                db.add(fac)
                db.commit()
                db.refresh(fac)
                print(f"✓ Created Faculty Profile: {fname}")
            faculty_map[femail] = fac

        # 7. Academic Term
        term = db.query(AcademicTerm).filter(AcademicTerm.institution_id == inst.id, AcademicTerm.name == "Fall 2026").first()
        if not term:
            term = AcademicTerm(
                institution_id=inst.id,
                name="Fall 2026",
                academic_year="2026-2027",
                term_type="semester",
                start_date=date(2026, 9, 1),
                end_date=date(2026, 12, 15),
                status="active",
            )
            db.add(term)
            db.commit()
            db.refresh(term)
            print("✓ Created Academic Term: Fall 2026")

        # 8. Courses
        courses_data = [
            ("CS301", "Computer Networks", dept_map["CS"].id, 4),
            ("CS302", "Database Systems", dept_map["CS"].id, 4),
            ("IT305", "Cyber Security", dept_map["IT"].id, 3),
            ("CS304", "Software Engineering", dept_map["CS"].id, 4),
        ]
        course_map = {}
        for ccode, cname, cdept, ccreds in courses_data:
            c = db.query(AcademicCourse).filter(AcademicCourse.institution_id == inst.id, AcademicCourse.code == ccode).first()
            if not c:
                c = AcademicCourse(
                    institution_id=inst.id,
                    department_id=cdept,
                    code=ccode,
                    name=cname,
                    credits=ccreds,
                    status="active",
                )
                db.add(c)
                db.commit()
                db.refresh(c)
                print(f"✓ Created Course: {ccode} — {cname}")
            course_map[ccode] = c

        # 9. Sections
        sections_data = [
            ("CS301", "CS301-A", 35),
            ("CS302", "CS302-A", 30),
            ("IT305", "IT305-B", 25),
            ("CS304", "CS304-A", 40),
        ]
        sec_map = {}
        for ccode, scode, scap in sections_data:
            sec = db.query(AcademicSection).filter(
                AcademicSection.institution_id == inst.id,
                AcademicSection.course_id == course_map[ccode].id,
                AcademicSection.section_code == scode,
            ).first()
            if not sec:
                sec = AcademicSection(
                    institution_id=inst.id,
                    course_id=course_map[ccode].id,
                    academic_term_id=term.id,
                    section_code=scode,
                    capacity=scap,
                    status="active",
                )
                db.add(sec)
                db.commit()
                db.refresh(sec)
                print(f"✓ Created Section: {scode} (Cap: {scap})")
            sec_map[scode] = sec

        # Assign Faculty to Sections
        faculty_assigns = [
            (sec_map["CS301-A"].id, faculty_map["sarah.jenkins@northbridge.edu"].id),
            (sec_map["CS302-A"].id, faculty_map["sarah.jenkins@northbridge.edu"].id),
            (sec_map["IT305-B"].id, faculty_map["alan.miller@northbridge.edu"].id),
            (sec_map["CS304-A"].id, faculty_map["maya.patel@northbridge.edu"].id),
        ]
        for s_id, f_id in faculty_assigns:
            assign = db.query(SectionFacultyAssignment).filter(
                SectionFacultyAssignment.section_id == s_id,
                SectionFacultyAssignment.faculty_id == f_id,
            ).first()
            if not assign:
                assign = SectionFacultyAssignment(
                    institution_id=inst.id,
                    section_id=s_id,
                    faculty_id=f_id,
                    role="primary_instructor",
                    is_primary=True,
                )
                db.add(assign)
                db.commit()

        # 10. Enrollments
        enroll_data = [
            (student_alex.id, sec_map["CS301-A"].id),
            (student_alex.id, sec_map["CS302-A"].id),
            (student_jordan.id, sec_map["CS301-A"].id),
            (student_jordan.id, sec_map["IT305-B"].id),
        ]
        for st_id, sc_id in enroll_data:
            enr = db.query(SectionEnrollment).filter(
                SectionEnrollment.student_id == st_id,
                SectionEnrollment.section_id == sc_id,
            ).first()
            if not enr:
                enr = SectionEnrollment(
                    institution_id=inst.id,
                    student_id=st_id,
                    section_id=sc_id,
                    status="enrolled",
                )
                db.add(enr)
                db.commit()
        print("✓ Enrolled Alex Taylor into CS301-A & CS302-A")
        print("✓ Enrolled Jordan Lee into CS301-A & IT305-B")

        # 11. Timetable & Published Version 1
        tt = db.query(Timetable).filter(
            Timetable.institution_id == inst.id,
            Timetable.academic_term_id == term.id,
        ).first()
        if not tt:
            tt = Timetable(
                institution_id=inst.id,
                academic_term_id=term.id,
                name="Northbridge Official Timetable Fall 2026",
                status="published",
            )
            db.add(tt)
            db.commit()
            db.refresh(tt)
            print("✓ Created Baseline Timetable")

        # Timetable Version 1 (Published)
        v1 = db.query(TimetableVersion).filter(
            TimetableVersion.timetable_id == tt.id,
            TimetableVersion.version_number == 1,
        ).first()
        if not v1:
            v1 = TimetableVersion(
                institution_id=inst.id,
                timetable_id=tt.id,
                version_number=1,
                name="Version 1.0 (Official Baseline)",
                status="published",
                published_at=datetime.now(timezone.utc),
                created_by_user_id=admin_user.id,
                change_summary="Official baseline timetable release for Fall 2026 term.",
            )
            db.add(v1)
            db.commit()
            db.refresh(v1)
            tt.published_version_id = v1.id
            db.commit()
            print("✓ Created Published Timetable Version 1.0")

        # Course Meetings for Version 1
        # Day: 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri
        meetings_data = [
            # CS301-A: Mon & Wed 09:00 - 10:30 in B204 (Jenkins)
            (sec_map["CS301-A"].id, room_map["B204"].id, faculty_map["sarah.jenkins@northbridge.edu"].id, 1, time(9, 0), time(10, 30)),
            (sec_map["CS301-A"].id, room_map["B204"].id, faculty_map["sarah.jenkins@northbridge.edu"].id, 3, time(9, 0), time(10, 30)),
            # CS302-A: Tue & Thu 11:00 - 12:30 in C101 (Jenkins)
            (sec_map["CS302-A"].id, room_map["C101"].id, faculty_map["sarah.jenkins@northbridge.edu"].id, 2, time(11, 0), time(12, 30)),
            (sec_map["CS302-A"].id, room_map["C101"].id, faculty_map["sarah.jenkins@northbridge.edu"].id, 4, time(11, 0), time(12, 30)),
            # IT305-B: Tue & Thu 14:00 - 15:30 in Lab-3 (Miller)
            (sec_map["IT305-B"].id, room_map["Lab-3"].id, faculty_map["alan.miller@northbridge.edu"].id, 2, time(14, 0), time(15, 30)),
            (sec_map["IT305-B"].id, room_map["Lab-3"].id, faculty_map["alan.miller@northbridge.edu"].id, 4, time(14, 0), time(15, 30)),
            # CS304-A: Fri 10:00 - 13:00 in B204 (Patel)
            (sec_map["CS304-A"].id, room_map["B204"].id, faculty_map["maya.patel@northbridge.edu"].id, 5, time(10, 0), time(13, 0)),
        ]
        for sec_id, r_id, fac_id, dow, st, et in meetings_data:
            cm = db.query(CourseMeeting).filter(
                CourseMeeting.timetable_id == tt.id,
                CourseMeeting.version_id == v1.id,
                CourseMeeting.section_id == sec_id,
                CourseMeeting.day_of_week == dow,
            ).first()
            if not cm:
                cm = CourseMeeting(
                    timetable_id=tt.id,
                    version_id=v1.id,
                    institution_id=inst.id,
                    section_id=sec_id,
                    room_id=r_id,
                    faculty_id=fac_id,
                    academic_term_id=term.id,
                    day_of_week=dow,
                    start_time=st,
                    end_time=et,
                    status="active",
                )
                db.add(cm)
                db.commit()
        print("✓ Created 7 official course meetings for Version 1")

        # 12. Student Profile & Personal Commitments (Alex Taylor)
        profile = db.query(StudentProfile).filter(
            StudentProfile.user_id == student_alex.id,
            StudentProfile.institution_id == inst.id,
        ).first()
        if not profile:
            profile = StudentProfile(
                user_id=student_alex.id,
                institution_id=inst.id,
                department_id=dept_map["CS"].id,
                student_number="NB-2026-0814",
                program="B.Sc. Computer Science",
                year_of_study=3,
                status="active",
            )
            db.add(profile)
            db.commit()

        # Alex Taylor's personal shifts (Tuesday & Thursday 17:00-21:00)
        shifts = [
            ("The Daily Grind Barista", 2, time(17, 0), time(21, 0), 16.50),
            ("The Daily Grind Barista", 4, time(17, 0), time(21, 0), 16.50),
        ]
        for title, dow, st, et, wage in shifts:
            tb = db.query(TimeBlock).filter(
                TimeBlock.user_id == student_alex.id,
                TimeBlock.title == title,
                TimeBlock.day_of_week == dow,
            ).first()
            if not tb:
                tb = TimeBlock(
                    user_id=student_alex.id,
                    title=title,
                    type=BlockType.SHIFT,
                    day_of_week=dow,
                    start_time=st,
                    end_time=et,
                    duration_minutes=240,
                    hourly_wage=wage,
                    location="Camden Coffee Lounge",
                    is_recurring=True,
                )
                db.add(tb)
                db.commit()
        print("✓ Seeded Student Work Shifts (Barista Tue & Thu 17:00–21:00)")

        # Alex Taylor's Study Tasks
        tasks = [
            ("Prepare Database Schema (CS302)", 2.0, "2026-09-18", "high"),
            ("Network Routing Lab Report (CS301)", 3.0, "2026-09-21", "medium"),
        ]
        for ttitle, dur, ddate, prio in tasks:
            st = db.query(StudyTask).filter(StudyTask.user_id == student_alex.id, StudyTask.title == ttitle).first()
            if not st:
                st = StudyTask(
                    user_id=student_alex.id,
                    title=ttitle,
                    total_hours_required=dur,
                    deadline=date.fromisoformat(ddate),
                    priority=prio,
                )
                db.add(st)
                db.commit()
        print("✓ Seeded Study Tasks for Smart Planning")

        # Initial Notification
        notif = db.query(NotificationLog).filter(
            NotificationLog.user_id == student_alex.id,
            NotificationLog.type == "TIMETABLE_UPDATE",
        ).first()
        if not notif:
            notif = NotificationLog(
                user_id=student_alex.id,
                institution_id=inst.id,
                timetable_version_id=v1.id,
                type="TIMETABLE_UPDATE",
                title="Fall 2026 Timetable Released",
                body="Northbridge University has published Version 1.0 of the official academic schedule.",
                channel="in_app",
                priority="INFO",
            )
            db.add(notif)
            db.commit()
            print("✓ Seeded Notification for Student")

        print("=" * 65)
        print("  Demo Seed Completed Successfully!")
        print("  Persona Credentials:")
        print("  - Admin:   admin@northbridge.edu            / Northbridge2026!")
        print("  - Faculty: faculty@northbridge.edu          / Faculty2026!")
        print("  - Student: alex.taylor@student.northbridge.edu / Student2026!")
        print("  - Student: jordan.lee@student.northbridge.edu   / Student2026!")
        print("=" * 65)

    finally:
        db.close()


if __name__ == "__main__":
    seed()
