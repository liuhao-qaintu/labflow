from fastapi import APIRouter, Depends
from app.schemes.auth import LoginRequest, RegisterRequest
from sqlalchemy.orm import Session
from app.database import get_db

from app.common.response import Response
from app.services import auth as auth_service


router = APIRouter(prefix="/auth" ,tags=["权限验证"])

@router.post('/login')
def login(data:LoginRequest,db:Session = Depends(get_db)):
    result = auth_service.login(db=db,data=data)
    return Response.success(
        data=result,
        message="登录成功",
    )

@router.post("/register")
def register(data:RegisterRequest,db:Session = Depends(get_db)):
    auth_service.register(db,data)
    return Response.success(message = "注册成功")


