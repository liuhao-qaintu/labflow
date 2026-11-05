from collections import OrderedDict
from datetime import timedelta
import hashlib
import hmac
import secrets
import threading
import time
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.config import settings
from app.models.user import User
from app.models.recovery import RecoveryRequest,RecoveryEvent,utcnow
from app.services import user_service
from app.schemes.user import UserResponse
from app.utils.jwt import credential_fingerprint
from app.utils.password import verify_password

QUERY_BUCKETS = OrderedDict()
QUERY_LOCK = threading.Lock()
OPEN_STATUSES = ('pending','need_more_info')


def iso(value):
    return value.isoformat() + 'Z'


def number(item):
    return f'LF-{item.id:08d}'


def ip_hash(ip):
    return hmac.new(settings.JWT_SECRET_KEY.encode(),('recovery-ip:' + ip).encode(),hashlib.sha256).hexdigest()


def limit_queries(ip):
    key = ip_hash(ip)
    now = time.monotonic()
    with QUERY_LOCK:
        attempts = [value for value in QUERY_BUCKETS.pop(key,[]) if now - value < 60]
        QUERY_BUCKETS[key] = attempts
        if len(attempts) >= 30:
            raise HTTPException(status_code=429,detail='操作过于频繁，请一分钟后重试')
        attempts.append(now)
        if len(QUERY_BUCKETS) > 2048:
            QUERY_BUCKETS.popitem(last=False)


def submit_request(db:Session,data,ip:str):
    limit_queries(ip)
    admin = db.query(User).filter(User.id == settings.PASSWORD_RECOVERY_ADMIN_ID,User.role == 'admin',User.status == 1).first()
    if not admin:
        raise HTTPException(status_code=503,detail='申请服务暂未开放，请联系所在实验室的管理员')
    now = utcnow()
    address = ip_hash(ip)
    ip_count = db.query(RecoveryRequest).filter(RecoveryRequest.ip_hash == address,RecoveryRequest.submitted_at > now - timedelta(hours=1)).count()
    name_count = db.query(RecoveryRequest).filter(RecoveryRequest.username == data.username,RecoveryRequest.submitted_at > now - timedelta(days=1)).count()
    if ip_count >= 10 or name_count >= 3:
        raise HTTPException(status_code=429,detail='提交次数过多，请使用已有凭据跟进申请，或稍后重试')
    credential = secrets.token_urlsafe(32)
    item = RecoveryRequest(**data.model_dump(),recipient_id=admin.id,ip_hash=address,
        credential_hash=hashlib.sha256(credential.encode()).hexdigest(),expires_at=now + timedelta(days=30))
    db.add(item)
    db.flush()
    db.add(RecoveryEvent(request_id=item.id,actor='applicant',action='submitted',content='申请已提交，等待管理员核验。'))
    db.commit()
    return {'number':number(item),'credential':credential,'expires_at':iso(item.expires_at)}


def get_by_credential(db:Session,credential:str,lock:bool=False):
    query = db.query(RecoveryRequest).filter(RecoveryRequest.credential_hash == hashlib.sha256(credential.encode()).hexdigest())
    item = query.with_for_update().first() if lock else query.first()
    if not item or item.expires_at <= utcnow():
        raise HTTPException(status_code=404,detail='申请凭据无效或已到期，请检查凭据或重新申请')
    return item


def public_detail(db:Session,item):
    events = db.query(RecoveryEvent).filter(RecoveryEvent.request_id == item.id).order_by(RecoveryEvent.id).all()
    result = {'number':number(item),'username':item.username,'status':item.status,
        'submitted_at':iso(item.submitted_at),'expires_at':iso(item.expires_at),
        'events':[{'actor':event.actor,'action':event.action,'content':event.content,'time':iso(event.occurred_at)} for event in events],
        'initial_password':None}
    # 凭据仅能访问本申请。只有管理员核验并重置后，才交付这次重置仍有效的初始密码。
    if item.status == 'resolved' and item.target_user_id and item.reset_version:
        user = db.query(User).filter(User.id == item.target_user_id,User.status == 1).first()
        if (user and user.must_change_password and
                hmac.compare_digest(item.reset_version,credential_fingerprint(user.password)) and
                settings.RESET_INITIAL_PASSWORD and verify_password(settings.RESET_INITIAL_PASSWORD,user.password)):
            result['initial_password'] = settings.RESET_INITIAL_PASSWORD
    return result


def lookup_request(db:Session,data,ip:str):
    limit_queries(ip)
    return public_detail(db,get_by_credential(db,data.credential.get_secret_value()))


def supplement_request(db:Session,data,ip:str):
    limit_queries(ip)
    item = get_by_credential(db,data.credential.get_secret_value(),lock=True)
    if item.status not in OPEN_STATUSES:
        raise HTTPException(status_code=409,detail='申请已结束，请勿重复补充')
    count = db.query(RecoveryEvent).filter(RecoveryEvent.request_id == item.id,RecoveryEvent.action == 'supplement',RecoveryEvent.occurred_at > utcnow() - timedelta(hours=1)).count()
    if count >= 5:
        raise HTTPException(status_code=429,detail='补充次数过多，请稍后重试')
    db.add(RecoveryEvent(request_id=item.id,actor='applicant',action='supplement',content=data.content))
    item.status = 'pending'
    db.commit()
    return public_detail(db,item)


def get_admin_request(db:Session,request_id:int,user:User,lock:bool=False):
    query = db.query(RecoveryRequest).filter(RecoveryRequest.id == request_id,RecoveryRequest.recipient_id == user.id)
    item = query.with_for_update().first() if lock else query.first()
    if not item:
        raise HTTPException(status_code=404,detail='申请不存在或不可访问')
    return item


def request_summary(item):
    return {'id':item.id,'number':number(item),'username':item.username,'name':item.name,
        'status':item.status,'submitted_at':iso(item.submitted_at),'expired':item.expires_at <= utcnow()}


def list_requests(db:Session,user:User,page:int,page_size:int,status:str | None):
    query = db.query(RecoveryRequest).filter(RecoveryRequest.recipient_id == user.id)
    pending = query.filter(RecoveryRequest.status == 'pending',RecoveryRequest.expires_at > utcnow()).count()
    if status:
        query = query.filter(RecoveryRequest.status == status)
    total = query.count()
    items = query.order_by(RecoveryRequest.id.desc()).offset((page-1)*page_size).limit(page_size).all()
    return {'list':[request_summary(item) for item in items],'total':total,'pending':pending}


def admin_detail(db:Session,request_id:int,user:User):
    item = get_admin_request(db,request_id,user)
    matches = db.query(User).filter(User.username == item.username).limit(2).all()
    account = None
    if len(matches) == 1:
        account = UserResponse.model_validate(matches[0]).model_copy(update={'can_reset_password':user_service.can_reset_password(user,matches[0])}).model_dump()
    result = public_detail(db,item)
    result.pop('initial_password')
    result.update({'id':item.id,'applicant':{'name':item.name,'email':item.email,'phone':item.phone,'description':item.description},
        'account':account,'expired':item.expires_at <= utcnow()})
    return result


def handle_request(db:Session,request_id:int,data,user:User):
    item = get_admin_request(db,request_id,user,lock=True)
    if item.status not in OPEN_STATUSES or item.expires_at <= utcnow():
        raise HTTPException(status_code=409,detail='申请已结束或已到期，不能重复处理')
    if data.action == 'reset':
        if not data.identity_verified:
            raise HTTPException(status_code=400,detail='请先核验申请人的账号归属')
        matches = db.query(User).filter(User.username == item.username).limit(2).all()
        if len(matches) != 1 or matches[0].id != data.target_user_id:
            raise HTTPException(status_code=400,detail='无法唯一定位所选账号，请先要求申请人核对用户名')
        target = user_service.reset_password(db,data.target_user_id,user,commit=False)
        item.target_user_id = target.id
        item.reset_version = credential_fingerprint(target.password)
        item.status = 'resolved'
    else:
        item.status = 'need_more_info' if data.action == 'need_more_info' else 'rejected'
    db.add(RecoveryEvent(request_id=item.id,actor='admin',actor_id=user.id,action=data.action,content=data.message))
    db.commit()
    return admin_detail(db,item.id,user)
