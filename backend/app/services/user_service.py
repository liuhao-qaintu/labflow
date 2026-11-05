from operator import or_

from app.models.user import User
from app.schemes.user import UserResponse,UserUpdateRequest,PasswordUpdateRequest,UserCreateRequest
from sqlalchemy.orm import Session
from app.utils.password import verify_password,hash_password
from app.common.exceptions import BusinessException
from app.common.response import PageResponse
from app.config import settings
from fastapi import HTTPException

def get_user_info (user:User) ->UserResponse:
    return UserResponse.model_validate(user)

def update_user_info (db:Session,user:User,data:UserUpdateRequest):
    user_dict  = data.model_dump(exclude_none=True,exclude={"role","status","password"})
    for field,value in user_dict.items():
        setattr(user,field,value)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)

def update_password (db:Session,user:User,data:PasswordUpdateRequest):
    if  not verify_password(data.old_password,user.password):
        raise BusinessException(message="原密码错误")
    if data.old_password == data.new_password:
        raise BusinessException(message= "两次密码不能重复")
    if len(data.new_password) < 8 or len(data.new_password.encode('utf-8')) > 72:
        raise BusinessException(message='新密码至少8个字符，且不超过72个UTF-8字节')
    if settings.RESET_INITIAL_PASSWORD and data.new_password == settings.RESET_INITIAL_PASSWORD:
        raise BusinessException(message='新密码不能使用管理员配置的初始密码')

    user.password = hash_password(data.new_password)
    user.must_change_password = False
    db.commit()


def can_reset_password(current_user:User,user:User):
    if current_user.role != 'admin' or user.status != 1:
        return False
    if user.role != 'student' or user.id in settings.DEVELOPER_USER_IDS:
        return current_user.id in settings.DEVELOPER_USER_IDS
    return True


def reset_password(db:Session,user_id:int,current_user:User,commit:bool=True):
    user = db.query(User).filter(User.id == user_id).with_for_update().populate_existing().first()
    if not user or user.status != 1:
        raise BusinessException(message='目标账号不存在或已停用')
    if not can_reset_password(current_user,user):
        raise HTTPException(status_code=403,detail='管理员或维护账号需由维护人员核验后重置')
    password = settings.RESET_INITIAL_PASSWORD
    if len(password) < 8 or len(password.encode('utf-8')) > 72:
        raise BusinessException(message='请先由维护人员配置有效的初始密码')
    user.password = hash_password(password)
    user.must_change_password = True
    if commit:
        db.commit()
    return user


def get_user_page_list(
        db:Session,page:int,page_size:int,keywords:str |None =None,current_user:User |None =None
):
    query = db.query(User)
    if keywords:
        query = query.filter(or_(User.username.ilike(f"%{keywords}%"),User.name.ilike(f"%{keywords}%")))
    total = query.count()
    items = (
        query.order_by(User.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    )
    return PageResponse(
        list = [UserResponse.model_validate(item).model_copy(update={
            'can_reset_password': bool(current_user and can_reset_password(current_user,item))
        }) for item in items],total =total
    )

def create_user(db:Session,data:UserCreateRequest):
    """新增用户"""
    exist = db.query(User).filter(data.username==User.username).first()
    if exist:
        raise BusinessException(message="用户已存在")

    user = User(
        username = data.username,
        password = hash_password(data.password),
        name=data.name,
        email  = data.email,
        phone = data.phone,
        role = data.role,
        avatar = data.avatar,
        status = data.status
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)

def update_user(db:Session,user_id:int,data:UserUpdateRequest):
    """更新用户（管理员）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BusinessException(message="用户不存在")
    payload = data.model_dump(exclude_none=True)
    for field,value in payload.items():
        setattr(user,field,value)

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)

def delete_user(db:Session,user_id:int,user:User):
    if user_id == user.id:
        raise BusinessException(message='不能删除当前登录的账号')
    user= db.query(User).filter(User.id ==user_id).first()
    if not user:
        raise BusinessException(message='用户不存在')
    db.delete(user)
    db.commit()
