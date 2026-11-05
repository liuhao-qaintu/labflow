from app.common.exceptions import BusinessException
from app.utils.password import verify_password,hash_password
from app.utils.jwt import create_access_token
from app.models.user import User
from app.schemes.user import UserResponse
from app.schemes.auth import loginResponse,LoginRequest,RegisterRequest
from sqlalchemy.orm import Session


def login(db:Session,data:LoginRequest) :
    user = db.query(User).where(User.username ==data.username).first()

    if not user:
        raise BusinessException(message="账号或者密码错误")
    if not verify_password(data.password, user.password):
        raise BusinessException(message="账号或者密码错误")
    if user.status != 1:
        raise BusinessException(message="账号被禁用")
    token = create_access_token(user.id, user.password)
    return  loginResponse(token=token,user = UserResponse.model_validate(user))

def register(db:Session,data:RegisterRequest):
    exists=db.query(User).where(User.username==data.username).filter().first()
    if exists:
        raise BusinessException(message = "账号已存在")

    user = User(
        username = data.username,
        password = hash_password(data.password),
        name = data.name or data.username,
        role = "student",
        status = 1,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
