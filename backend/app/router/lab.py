from fastapi import Depends,APIRouter
from app.models.lab import Lab
from app.dependencies.auth import get_current_user,get_current_admin
from app.schemes.lab import LabResponse,LabUpdateRequest,LabCreateRequest
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import lab_service
from app.common.response import Response

router = APIRouter(prefix="/lab",tags=["实验室管理"])


@router.get("/list")
def get_lab_list(
    page:int=1,
    page_size:int=10,
    keywords:str |None =None,
    current_user:Lab =Depends(get_current_user),
    db:Session =Depends(get_db),
    status:int | None = None
    ):
    res = lab_service.get_lab_page_list(db,page,page_size,keywords,status)
    return Response.success(data=res)

@router.post("")
def create_lab(
    data:LabCreateRequest,
    db:Session=Depends(get_db),
    current_user: Lab = Depends(get_current_admin)
):
    res = lab_service.create_lab(data=data,db=db )
    return Response.success(data=res)

@router.put("/{lab_id}")
def update_lab(
    lab_id:int,
    data:LabUpdateRequest,
    db:Session = Depends(get_db),
    current_user : Lab = Depends(get_current_admin)
):
    res = lab_service.update_lab(data=data,lab_id=lab_id,db=db)
    return Response.success(data=res)

@router.get("/{lab_id}")
def get_lab(
    lab_id:int,
    db:Session = Depends(get_db),
    current_user : Lab = Depends(get_current_user)
):
    res = lab_service.get_lab(lab_id=lab_id,db=db)
    return Response.success(data=res)


@router.delete("/{lab_id}")
def delete_lab(
    lab_id:int,
    db:Session = Depends(get_db),
    current_user:Lab = Depends(get_current_admin)
):
    res =lab_service.delete_lab(db,lab_id)
    return Response.success(message="删除成功")