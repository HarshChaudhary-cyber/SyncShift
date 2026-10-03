"""Additive role experience data; never contains another user's private tasks."""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint, func
from app.database import Base


class ProfessionalProfile(Base):
    __tablename__ = "professional_profiles"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    introduction = Column(Text, nullable=False, default="")
    specializations = Column(String(1000), nullable=False, default="")
    professional_phone = Column(String(64), nullable=False, default="")
    office_hours = Column(String(500), nullable=False, default="")
    office_location = Column(String(255), nullable=False, default="")


class AcademicInvitation(Base):
    __tablename__ = "academic_invitations"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime)


class LectureRecord(Base):
    __tablename__ = "lecture_records"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("class_workspaces.id"), nullable=False, index=True)
    event_key = Column(String(64), nullable=False)
    event_date = Column(Date, nullable=False)
    status = Column(String(16), nullable=False)
    minutes = Column(Integer, nullable=False)
    recorded_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("class_id", "event_key", "event_date", name="uq_lecture_occurrence"),)


class AcademicHistory(Base):
    __tablename__ = "academic_history"
    id = Column(Integer, primary_key=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), index=True)
    class_id = Column(Integer, ForeignKey("class_workspaces.id"), index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(64), nullable=False)
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class SharedAppointment(Base):
    __tablename__ = "shared_appointments"
    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False, default="")
    event_date = Column(Date, nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)


class AppointmentAudience(Base):
    __tablename__ = "appointment_audiences"
    appointment_id = Column(Integer, ForeignKey("shared_appointments.id"), primary_key=True)
    class_id = Column(Integer, ForeignKey("class_workspaces.id"), primary_key=True)
