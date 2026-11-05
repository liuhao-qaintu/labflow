from fastapi import FastAPI,Depends,APIRouter
from app.models.user import User
from app.dependencies.auth import get_current_user,get_current_admin,get_authenticated_user
from app.schemes.user import UserResponse,UserUpdateRequest,PasswordUpdateRequest,UserCreateRequest,PasswordResetRequest
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import user_service
from app.common.response import Response

router = APIRouter(prefix="/user",tags=["用户信息"])

@router.get("/me")
def get_user_info (current_user: User = Depends(get_authenticated_user)):
    return Response.success(data = user_service.get_user_info(current_user))

@router.put("/me")
def update_user_info (
    data:UserUpdateRequest,
    current_user:User = Depends(get_current_user),
    db:Session = Depends(get_db)
):
    """更新当前用户信息"""
    res = user_service.update_user_info(db,current_user,data)
    return Response.success(data=res)

@router.put("/password")
def update_password(
    data:PasswordUpdateRequest,
    current_user:User = Depends(get_authenticated_user),
    db:Session = Depends(get_db)
):
    """修改当前密码"""
    user_service.update_password(db=db,data=data,user=current_user)
    return Response.success(message="密码修改成功")

@router.get("/list")
def get_user_list(
    page:int=1,
    page_size:int=10,
    keywords:str |None =None,
    current_use:User =Depends(get_current_admin),
    db:Session =Depends(get_db)
    ):
    res = user_service.get_user_page_list(db,page,page_size,keywords,current_use)
    return Response.success(data=res)

@router.post("")
def create_user(
    data:UserCreateRequest,
    db:Session=Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    res = user_service.create_user(data=data,db=db )
    return Response.success(data=res)

@router.put("/{user_id}")
def update_user(
    user_id:int,
    data:UserUpdateRequest,
    db:Session = Depends(get_db),
    current_user : User = Depends(get_current_admin)
):
    res = user_service.update_user(data=data,user_id=user_id,db=db)
    return Response.success(data=res)


@router.delete("/{user_id}")
def delete_user(
    user_id:int,
    db:Session = Depends(get_db),
    current_user:User = Depends(get_current_admin)
):
    res =user_service.delete_user(db,user_id,user = current_user)
    return Response.success()


@router.put('/{user_id}/password/reset')
def reset_password(
    user_id:int,
    data:PasswordResetRequest,
    db:Session = Depends(get_db),
    current_user:User = Depends(get_current_admin)
):
    user_service.reset_password(db,user_id,current_user)
    return Response.success(message='密码已重置，请将初始密码告知已核验的账号本人；首次登录需修改密码')
