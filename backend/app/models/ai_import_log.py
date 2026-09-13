from sqlalchemy import BigInteger, Column, DateTime, Integer, String, func
from app.database import Base


class AIImportLog(Base):
    __tablename__ = "ai_import_logs"

    id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        index=True,
        autoincrement=True,
    )
    user_id = Column(
        BigInteger().with_variant(Integer, "sqlite"),
        index=True,
        nullable=False,
    )
    file_type = Column(String(32), nullable=False)
    file_size = Column(Integer, nullable=False)
    events_extracted = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
