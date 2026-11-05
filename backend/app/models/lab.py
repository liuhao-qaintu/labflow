from app.database import Base
from sqlalchemy.orm import Mapped,mapped_column
from sqlalchemy import Integer, String
from typing import Optional

class Lab(Base):
    __tablename__ = "labs"
    __table_args__ = {"comment":"实验室信息表"}

    name:Mapped[str] = mapped_column(String(50),comment="实验室名称",nullable=False)
    description:Mapped[Optional[str]] = mapped_column(String(500),comment="实验室描述",nullable=True)
    capacity:Mapped[int] = mapped_column(Integer,comment="实验室容量")
    open_time:Mapped[Optional[str]] = mapped_column(String(20),comment="开放时间")
    close_time:Mapped[Optional[str]] = mapped_column(String(20),comment="关闭时间")
    location:Mapped[Optional[str]] = mapped_column(String(100),comment="实验室地点")
    img:Mapped[Optional[str]] = mapped_column(String(200),comment="封面图")
    status:Mapped[str] = mapped_column(default=1,comment="状态:0-关闭，1-开启")
   