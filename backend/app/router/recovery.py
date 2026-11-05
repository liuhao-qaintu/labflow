from fastapi import APIRouter,Depends,Request,Response as HTTPResponse,Query
from sqlalchemy.orm import Session
from app.common.response import Response
from app.database import get_db
from app.dependencies.auth import get_current_admin
from app.models.user import User
from app.schemes.recovery import RecoverySubmitRequest,RecoveryLookupRequest,RecoverySupplementRequest,RecoveryHandleRequest
from app.services import recovery_service

router = APIRouter(tags=['找回密码申请'])


def no_store(response:HTTPResponse):
    response.headers['Cache-Control'] = 'no-store'


@router.post('/auth/recovery/requests',dependencies=[Depends(no_store)])
def submit_request(data:RecoverySubmitRequest,request:Request,db:Session=Depends(get_db)):
    result = recovery_service.submit_request(db,data,request.client.host if request.client else 'unknown')
    return Response.success(message='申请已提交，请保存凭据并在此跟进；提交不代表身份核验通过',data=result)


@router.post('/auth/recovery/lookup',dependencies=[Depends(no_store)])
def lookup_request(data:RecoveryLookupRequest,request:Request,db:Session=Depends(get_db)):
    return Response.success(data=recovery_service.lookup_request(db,data,request.client.host if request.client else 'unknown'))


@router.post('/auth/recovery/supplement',dependencies=[Depends(no_store)])
def supplement_request(data:RecoverySupplementRequest,request:Request,db:Session=Depends(get_db)):
    return Response.success(message='补充材料已提交',data=recovery_service.supplement_request(db,data,request.client.host if request.client else 'unknown'))


@router.get('/user/recovery/requests',dependencies=[Depends(no_store)])
def list_requests(page:int=Query(default=1,ge=1),page_size:int=Query(default=10,ge=1,le=50),
    status:str | None=Query(default=None,pattern='^(pending|need_more_info|resolved|rejected)$'),
    db:Session=Depends(get_db),current_user:User=Depends(get_current_admin)):
    return Response.success(data=recovery_service.list_requests(db,current_user,page,page_size,status))


@router.get('/user/recovery/requests/{request_id}',dependencies=[Depends(no_store)])
def request_detail(request_id:int,db:Session=Depends(get_db),current_user:User=Depends(get_current_admin)):
    return Response.success(data=recovery_service.admin_detail(db,request_id,current_user))


@router.put('/user/recovery/requests/{request_id}',dependencies=[Depends(no_store)])
def handle_request(request_id:int,data:RecoveryHandleRequest,db:Session=Depends(get_db),current_user:User=Depends(get_current_admin)):
    return Response.success(message='申请已处理',data=recovery_service.handle_request(db,request_id,data,current_user))
