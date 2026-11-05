from app.database import Base
from sqlalchemy import ForeignKey,String,Integer
from sqlalchemy.orm import mapped_column,Mapped ,relationship
from typing import Optional


from app.models.equipment import  Equipment
from app.models.lab import Lab
from app.models.user import User

class Reservation(Base):
    __tablename__= "reservations"
    __table_args__={"comment":"预约信息"}

    user_id:Mapped[int] = mapped_column(ForeignKey("users.id"),comment="预约人")
    lab_id:Mapped[int] = mapped_column(ForeignKey("labs.id"),comment="预约实验室")
    equipment_id:Mapped[Optional[int]] = mapped_column(ForeignKey("equipments.id"),comment="预约设备，空表示预约实验室")
    date:Mapped[str] = mapped_column(String(20),comment="预约日期")
    start_time:Mapped[str] = mapped_column(String(20),comment="开始时间")
    end_time:Mapped[str] = mapped_column(String(20),comment="结束时间")
    remark:Mapped[Optional[str]] = mapped_column(String(255),comment="备注")
    status:Mapped[int] = mapped_column(Integer, comment="预约状态 0待审核，1已通过，2已拒绝，3已取消",default=0)

    user : Mapped[User] = relationship()
    lab : Mapped[Lab] = relationship()
    equipment : Mapped[Equipment] = relationship()