from app.database import Base
from sqlalchemy.orm import Mapped,mapped_column,relationship
from sqlalchemy import Integer, String,ForeignKey
from typing import Optional
from app.models.lab import Lab

class Equipment(Base):
    __tablename__ = "equipments"
    __table_args__ = {"comment":"实验室设备表"}

    lab_id:Mapped[int]=mapped_column(ForeignKey("labs.id"),comment="所属实验室",nullable=False)
    name:Mapped[str] = mapped_column(String(50),comment="设备名称",nullable=False)
    description:Mapped[Optional[str]] = mapped_column(String(500),comment="设备描述",nullable=True)
    img:Mapped[Optional[str]] = mapped_column(String(200),comment="设备图")
    spec:Mapped[Optional[str]] = mapped_column(String(100),comment="设备型号")
    quantity:Mapped[Optional[str]] = mapped_column(Integer,comment="设备数量",default=1)
    status:Mapped[str] = mapped_column(Integer,default=1,comment="状态:0-维修，1-正常")
    lab:Mapped[Lab] = relationship()