import jwt
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from app.config import settings



def credential_fingerprint(password_hash: str) -> str:
    return hmac.new(settings.JWT_SECRET_KEY.encode(), b'credential-version\0' + password_hash.encode(), hashlib.sha256).hexdigest()


def create_access_token(user_id:int, password_hash: str):
    """创建JWT token"""
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)


    payload = {
        "user_id":user_id,
        "credential_version": credential_fingerprint(password_hash),
        "exp":expire,
    }#exp是固定key，不能写成别的

    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )

def decode_access_token(token):
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
