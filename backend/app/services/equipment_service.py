from operator import or_

from app.models.equipment import Equipment
from app.schemes.equipment import EquipmentResponse,EquipmentUpdateRequest,EquipmentCreateRequest
from sqlalchemy.orm import Session
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.models.lab import Lab


def get_equipment_page_list(
        db:Session,page:int,page_size:int,keywords:str |None =None,lab_id:int | None=None
):
    query = db.query(Equipment)
    if lab_id:
        query = query.filter(Equipment.lab_id == lab_id)
    if keywords:
        query = query.filter(or_(Equipment.name.ilike(f"%{keywords}%"),Equipment.name.ilike(f"%{keywords}%")))
    total = query.count()
    items = (
        query.order_by(Equipment.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    )
    results = []
    for item in items:
        res = EquipmentResponse.model_validate(item)
        res.lab_name = item.lab.name if item.lab else None
        results.append(res)


    return PageResponse(
        list = results,total =total
    )

def create_equipment(db:Session,data:EquipmentCreateRequest):
    """新增"""
    exist = db.query(Equipment).filter(Equipment.lab_id==data.lab_id,Equipment.name==data.name).first()
    if exist:
        raise BusinessException(message="实验设备已存在")

    equipment = Equipment(**data.model_dump())
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    res =EquipmentResponse.model_validate(equipment)
    res.lab_name = equipment.lab.name if equipment.lab else None
    return res

def update_equipment(db:Session,equipment_id:int,data:EquipmentUpdateRequest):
    """更新实验室（管理员）"""
    equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equipment:
        raise BusinessException(message="实验设备不存在")
    payload = data.model_dump(exclude_none=True)
    lab_id = payload.get("lab_id",equipment.lab_id)
    name = payload.get("name",equipment.name)
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise BusinessException(message="实验室不存在")
    exist = db.query(Equipment).filter(Equipment.lab_id ==lab_id,Equipment.name ==name,Equipment.id!=equipment_id).first()
    if exist:
        raise BusinessException(message="同一个实验室不能存在相同的设备")
    for field,value in payload.items():
        setattr(equipment,field,value)

    db.commit()
    db.refresh(equipment)
    res =EquipmentResponse.model_validate(equipment)
    res.lab_name = equipment.lab.name if equipment.lab else None
    return res

def delete_equipment(db:Session,equipment_id:int):
    equipment= db.query(Equipment).filter(Equipment.id ==equipment_id).first()
    if not equipment:
        raise BusinessException(message='实验室不存在')
    db.delete(equipment)
    db.commit()