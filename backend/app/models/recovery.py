from datetime import datetime,timezone
from sqlalchemy import String,Integer,Text,DateTime,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from app.database import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RecoveryRequest(Base):
    __tablename__ = 'password_recovery_requests'

    username:Mapped[str] = mapped_column(String(50),index=True)
    name:Mapped[str] = mapped_column(String(50),default='')
    email:Mapped[str] = mapped_column(String(100),default='')
    phone:Mapped[str] = mapped_column(String(30),default='')
    description:Mapped[str] = mapped_column(Text,default='')
    recipient_id:Mapped[int] = mapped_column(Integer,index=True)
    credential_hash:Mapped[str] = mapped_column(String(64),unique=True)
    ip_hash:Mapped[str] = mapped_column(String(64),index=True)
    status:Mapped[str] = mapped_column(String(20),default='pending',index=True)
    submitted_at:Mapped[datetime] = mapped_column(DateTime,default=utcnow,index=True)
    expires_at:Mapped[datetime] = mapped_column(DateTime)
    target_user_id:Mapped[int | None] = mapped_column(Integer,nullable=True)
    reset_version:Mapped[str | None] = mapped_column(String(64),nullable=True)


class RecoveryEvent(Base):
    __tablename__ = 'password_recovery_events'

    request_id:Mapped[int] = mapped_column(ForeignKey('password_recovery_requests.id'),index=True)
    actor:Mapped[str] = mapped_column(String(20))
    actor_id:Mapped[int | None] = mapped_column(Integer,nullable=True)
    action:Mapped[str] = mapped_column(String(30))
    content:Mapped[str] = mapped_column(Text)
    occurred_at:Mapped[datetime] = mapped_column(DateTime,default=utcnow)
