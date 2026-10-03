"""Shared class records. Personal schedules never belong to a workspace."""
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey, UniqueConstraint, func
from app.database import Base


class ClassWorkspace(Base):
    __tablename__ = "class_workspaces"
    id = Column(Integer, primary_key=True)
    name = Column(String(160), nullable=False)
    description = Column(Text, nullable=False, default="")
    join_code = Column(String(64), unique=True, nullable=False)
    section_id = Column(Integer, ForeignKey("academic_sections.id"), unique=True, nullable=True)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    course_id = Column(Integer, ForeignKey("academic_courses.id"), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ClassMember(Base):
    __tablename__ = "class_members"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("class_workspaces.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # 'removed' explicitly revokes a compatibility membership without destroying history.
    role = Column(String(16), nullable=False, default="learner")
    __table_args__ = (UniqueConstraint("class_id", "user_id", name="uq_class_member"),)


class ClassEvent(Base):
    __tablename__ = "class_events"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("class_workspaces.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False, default="")
    event_date = Column(Date, nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    status = Column(String(16), nullable=False, default="draft")
    # Edits to a published event stay private until the instructor publishes them.
    pending_json = Column(Text, nullable=True)


class ClassAnnouncement(Base):
    __tablename__ = "class_announcements"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("class_workspaces.id"), nullable=False, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(160), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class ClassInvitation(Base):
    __tablename__ = "class_invitations"
    id = Column(Integer, primary_key=True)
    class_id = Column(Integer, ForeignKey("class_workspaces.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    role = Column(String(16), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
