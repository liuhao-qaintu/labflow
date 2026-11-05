from app.database import Base
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import Integer, String, Boolean, text

class User(Base):
    __tablename__ = "users"
    __table_args__ = {"comment":"用户信息表"}

    username:Mapped[str] = mapped_column(String(50),comment="账号",nullable=False)
    password: Mapped[str] = mapped_column(String(255), comment="密码哈希", nullable=False)
    name:Mapped[str] = mapped_column(String(50),comment="名称",nullable=False)
    role:Mapped[str] = mapped_column(String(50),comment="角色：student-学生，admin-管理员",nullable=False)
    email:Mapped[str|None] = mapped_column(String(50),comment="邮箱",nullable=True)
    phone:Mapped[str|None] = mapped_column(String(50),comment="手机号",nullable=True)
    avatar:Mapped[str|None] = mapped_column(String(50),comment="头像",nullable=True)
    status: Mapped[int] = mapped_column(Integer, default=1, comment="状态：0-禁用，1-正常")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text('0'), comment="是否需要先修改初始密码")
