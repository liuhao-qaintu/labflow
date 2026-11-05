import jwt
import hmac
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.utils.jwt import decode_access_token, credential_fingerprint

from app.common.exceptions import BusinessException
from app.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="router/auth/login")


def get_authenticated_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """JWT鉴权验证合法性"""
    try:
        payload = decode_access_token(token)
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录已失效,请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户被禁用",
        )

    version = payload.get('credential_version')
    if not isinstance(version, str) or not hmac.compare_digest(version, credential_fingerprint(user.password)):
        raise HTTPException(status_code=401, detail='登录状态已更新，请重新登录',
                            headers={'WWW-Authenticate': 'Bearer'})
    return user


def get_current_user(current_user: User = Depends(get_authenticated_user)) -> User:
    if current_user.must_change_password:
        raise HTTPException(status_code=428, detail='请先修改初始密码')
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)) ->User :
    """后端核对资源管理员角色，前端菜单状态不作为授权依据。"""
    if current_user.role != "admin" :
        raise HTTPException(status_code=403, detail="无权限访问")
    return current_user


def get_current_developer(current_user: User = Depends(get_current_admin)) -> User:
    if current_user.id not in settings.DEVELOPER_USER_IDS:
        raise HTTPException(status_code=403, detail="此功能仅供维护人员使用")
    return current_user
