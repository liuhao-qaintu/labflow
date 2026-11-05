from fastapi import APIRouter,Depends
from sqlalchemy.orm  import  Session

from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_user,get_current_admin
from app.schemes.reservation import ReservationCreationRequest,ReservationResponse,AuditReservationRequest
from app.models.user import User
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.services import reservation_service

router = APIRouter(prefix='/reservation',tags=["预约相关接口"])

@router.post("")
def create_reservation(data:ReservationCreationRequest,
                        db:Session = Depends(get_db),
                        user:User = Depends(get_current_user)):
    reservation_service.create_reservation(data=data,db=db,current_use=user)
    return Response.success()

@router.get("/list")
def get_reseavation_page_list(page:int=1,
                              page_size:int =10,
                              status:int |None=None,
                              db:Session = Depends(get_db),
                              user:User = Depends(get_current_user)):
    res = reservation_service.get_reservation_page_list(page=page,page_size=page_size,status=status,current_user=user,db=db)
    return Response.success(data=res)

@router.put("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id:int,
    db:Session=Depends(get_db),
    user:User =Depends(get_current_user)
):
    reservation_service.cancel_reservation(reservation_id=reservation_id,current_user=user,db=db)
    return Response.success()

@router.put("/{reservation_id}/audit")
def audit_reservation(
    reservation_id:int,
    data:AuditReservationRequest,
    db:Session = Depends(get_db),
    user:User = Depends(get_current_admin)
):
    reservation_service.audit_reservation(reservation_id=reservation_id,status=data.status,db=db)
    return Response.success()