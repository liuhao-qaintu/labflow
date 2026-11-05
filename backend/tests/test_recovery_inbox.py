"""站内找回申请：内存库与测试签名，不操作真实账号或真实申请。"""
import hashlib
import sys
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi import FastAPI,HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.common.exceptions import BusinessException,business_exception_handler,http_exception_handler,validation_exception_handler
from app.config import settings
from app.database import Base,get_db
from app.models.user import User
from app.models.recovery import RecoveryRequest,RecoveryEvent,utcnow
from app.router import router
from app.services import recovery_service
from app.utils.password import hash_password,verify_password
from app.utils.jwt import create_access_token

OLD='TEST_ONLY_original_password_789!'
INITIAL='TEST_ONLY_initial_password_123!'
NEW='TEST_ONLY_changed_password_456!'
KEY='TEST_ONLY_signing_key_for_in_memory_recovery_tests'

class RecoveryInboxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_hash=hash_password(OLD)

    def setUp(self):
        self.engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False})
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            db.add_all([User(id=10,username='receiver',name='Receiver',role='admin',status=1,password=self.old_hash),
                        User(id=20,username='reader',name='RegisteredName',email='private@example.test',phone='13800000000',role='student',status=1,password=self.old_hash),
                        User(id=30,username='otheradmin',name='Other',role='admin',status=1,password=self.old_hash)])
            db.commit()
        for name,value in [('JWT_SECRET_KEY',KEY),('PASSWORD_RECOVERY_ADMIN_ID',10),('RESET_INITIAL_PASSWORD',INITIAL),('DEVELOPER_USER_IDS',[])]:
            option=patch.object(settings,name,value);option.start();self.addCleanup(option.stop)
        recovery_service.QUERY_BUCKETS.clear()
        self.app=FastAPI()
        self.app.include_router(router)
        for error,handler in [(BusinessException,business_exception_handler),(HTTPException,http_exception_handler),(RequestValidationError,validation_exception_handler)]:
            self.app.add_exception_handler(error,handler)
        def database():
            with Session(self.engine) as db:yield db
        self.app.dependency_overrides[get_db]=database
        self.client=TestClient(self.app)
        self.addCleanup(self.client.close);self.addCleanup(self.engine.dispose)

    def headers(self,uid=10):
        with Session(self.engine) as db:token=create_access_token(uid,db.get(User,uid).password)
        return {'Authorization':'Bearer '+token}

    def submit(self,username='reader',**fields):
        response=self.client.post('/router/auth/recovery/requests',json={'username':username,**fields})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.headers.get('cache-control'),'no-store')
        self.assertEqual(response.json()['code'],200)
        return response.json()['data']

    def request_id(self,credential):
        with Session(self.engine) as db:
            return db.query(RecoveryRequest).filter_by(credential_hash=hashlib.sha256(credential.encode()).hexdigest()).one().id

    def lookup(self,credential):
        return self.client.post('/router/auth/recovery/lookup',json={'credential':credential})

    def handle(self,credential,action='need_more_info',**fields):
        request_id=self.request_id(credential)
        return self.client.put(f'/router/user/recovery/requests/{request_id}',headers=self.headers(),json={'action':action,'message':'TEST_ONLY 管理员处理说明',**fields})

    def approve(self,credential):
        result=self.handle(credential,'reset',identity_verified=True,target_user_id=20)
        self.assertEqual(result.json()['code'],200,result.text)
        return result

    def test_username_only_submission_and_no_account_information_leak(self):
        existing=self.submit()
        missing=self.submit('no_such_account')
        self.assertEqual(set(existing),set(missing))
        for receipt in (existing,missing):
            detail=self.lookup(receipt['credential']).json()['data']
            self.assertEqual(detail['status'],'pending')
            self.assertIsNone(detail['initial_password'])
            self.assertNotIn('account',detail)
            self.assertNotIn('private@example.test',str(detail))
            self.assertNotIn('13800000000',str(detail))

    def test_credential_is_random_hashed_and_expires_after_thirty_days(self):
        first=self.submit();second=self.submit()
        self.assertNotEqual(first['credential'],second['credential'])
        self.assertEqual(len(first['credential']),43)
        with Session(self.engine) as db:
            item=db.get(RecoveryRequest,self.request_id(first['credential']))
            self.assertEqual(item.credential_hash,hashlib.sha256(first['credential'].encode()).hexdigest())
            self.assertNotEqual(item.credential_hash,first['credential'])
            self.assertTrue(29<=(item.expires_at-utcnow()).total_seconds()/86400<=30)
            self.assertEqual(item.recipient_id,10)
            self.assertEqual(db.get(User,20).password,self.old_hash)

    def test_public_client_cannot_select_recipient_or_set_status(self):
        for extra in ({'recipient_id':30},{'status':'resolved'},{'target_user_id':20}):
            result=self.client.post('/router/auth/recovery/requests',json={'username':'reader',**extra})
            self.assertEqual(result.status_code,422)

    def test_required_username_and_optional_field_validation(self):
        for data in ({},{'username':'   '},{'username':'a'*51},{'username':'reader','email':'bad'},{'username':'reader','phone':'letters'},{'username':'reader','description':'x'*1501}):
            self.assertEqual(self.client.post('/router/auth/recovery/requests',json=data).status_code,422)

    def test_recipient_configuration_must_point_to_active_admin(self):
        for uid in (None,20,999):
            with patch.object(settings,'PASSWORD_RECOVERY_ADMIN_ID',uid):
                self.assertEqual(self.client.post('/router/auth/recovery/requests',json={'username':'reader'}).status_code,503)
        with Session(self.engine) as db: self.assertEqual(db.query(RecoveryRequest).count(),0)

    def test_other_admin_and_student_cannot_read_or_handle_recipient_requests(self):
        receipt=self.submit();rid=self.request_id(receipt['credential'])
        path=f'/router/user/recovery/requests/{rid}'
        self.assertEqual(self.client.get(path).status_code,401)
        self.assertEqual(self.client.get(path,headers=self.headers(20)).status_code,403)
        self.assertEqual(self.client.get(path,headers=self.headers(30)).status_code,404)
        response=self.client.put(path,headers=self.headers(30),json={'action':'reject','message':'spoofed'})
        self.assertEqual(response.status_code,404)
        self.assertEqual(self.client.get('/router/user/recovery/requests',headers=self.headers(30)).json()['data']['total'],0)

    def test_admin_detail_separates_claimed_and_registered_information(self):
        receipt=self.submit(name='ClaimedName',email='claimed@example.test',description='TEST_ONLY 申请说明')
        response=self.client.get(f'/router/user/recovery/requests/{self.request_id(receipt["credential"])}',headers=self.headers())
        data=response.json()['data']
        self.assertEqual(response.headers.get('cache-control'),'no-store')
        self.assertEqual(data['applicant']['name'],'ClaimedName')
        self.assertEqual(data['account']['name'],'RegisteredName')
        self.assertNotIn('credential_hash',response.text)
        self.assertNotIn(receipt['credential'],response.text)
        self.assertNotIn(self.old_hash,response.text)

    def test_followup_timeline_and_pending_count(self):
        receipt=self.submit();credential=receipt['credential']
        response=self.handle(credential,message='请补充实验室登记信息')
        self.assertEqual(response.json()['data']['status'],'need_more_info')
        self.assertEqual(self.client.get('/router/user/recovery/requests',headers=self.headers()).json()['data']['pending'],0)
        response=self.client.post('/router/auth/recovery/supplement',json={'credential':credential,'content':'TEST_ONLY 实验室证明说明'})
        self.assertEqual(response.json()['data']['status'],'pending')
        detail=self.lookup(credential).json()['data']
        self.assertEqual([event['action'] for event in detail['events']],['submitted','need_more_info','supplement'])
        self.assertEqual(self.client.get('/router/user/recovery/requests',headers=self.headers()).json()['data']['pending'],1)

    def test_lookup_requires_full_secret_not_request_number_or_username(self):
        receipt=self.submit()
        for credential in (receipt['number'],'reader','x'*43):
            self.assertIn(self.lookup(credential).status_code,(404,422))
        response=self.client.post('/router/auth/recovery/lookup',json={'credential':receipt['credential'],'username':'someone_else'})
        self.assertEqual(response.status_code,422)

    def test_expired_and_unknown_credentials_have_same_response(self):
        receipt=self.submit();credential=receipt['credential']
        with Session(self.engine) as db:
            db.get(RecoveryRequest,self.request_id(credential)).expires_at=utcnow()-timedelta(seconds=1);db.commit()
        expired=self.lookup(credential);unknown=self.lookup('x'*43)
        self.assertEqual(expired.status_code,404)
        self.assertEqual(expired.json(),unknown.json())
        self.assertEqual(self.handle(credential).status_code,409)

    def test_submission_does_not_change_password_or_allow_login(self):
        receipt=self.submit()
        response=self.client.post('/router/auth/login',json={'username':'reader','password':receipt['credential']})
        self.assertNotEqual(response.json()['code'],200)
        self.assertEqual(self.client.get('/router/user/me',headers={'Authorization':'Bearer '+receipt['credential']}).status_code,401)
        with Session(self.engine) as db:
            self.assertEqual(db.get(User,20).password,self.old_hash)
            self.assertFalse(db.get(User,20).must_change_password)

    def test_reset_requires_independent_verification_and_exact_target(self):
        receipt=self.submit();credential=receipt['credential']
        for data in ({'target_user_id':20},{'identity_verified':True,'target_user_id':30}):
            self.assertEqual(self.handle(credential,'reset',**data).status_code,400)
        with Session(self.engine) as db:
            self.assertEqual(db.get(User,20).password,self.old_hash)
            self.assertEqual(db.get(RecoveryRequest,self.request_id(credential)).status,'pending')

    def test_only_verified_reset_delivers_initial_password_and_revokes_prior_login(self):
        old_headers=self.headers(20)
        credential=self.submit()['credential']
        self.approve(credential)
        response=self.lookup(credential)
        self.assertEqual(response.headers.get('cache-control'),'no-store')
        self.assertEqual(response.json()['data']['initial_password'],INITIAL)
        self.assertEqual(self.client.get('/router/user/me',headers=old_headers).status_code,401)
        with Session(self.engine) as db:self.assertTrue(verify_password(INITIAL,db.get(User,20).password))
        self.assertEqual(self.handle(credential,'reset',identity_verified=True,target_user_id=20).status_code,409)

    def test_after_password_change_no_initial_password_is_exposed(self):
        credential=self.submit()['credential'];self.approve(credential)
        response=self.client.put('/router/user/password',headers=self.headers(20),json={'old_password':INITIAL,'new_password':NEW})
        self.assertEqual(response.json()['code'],200)
        self.assertIsNone(self.lookup(credential).json()['data']['initial_password'])

    def test_later_reset_does_not_deliver_password_to_old_request(self):
        old=self.submit()['credential'];self.approve(old)
        latest=self.submit()['credential'];self.approve(latest)
        self.assertIsNone(self.lookup(old).json()['data']['initial_password'])
        self.assertEqual(self.lookup(latest).json()['data']['initial_password'],INITIAL)

    def test_changed_initial_configuration_does_not_deliver_wrong_password(self):
        credential=self.submit()['credential'];self.approve(credential)
        with patch.object(settings,'RESET_INITIAL_PASSWORD','TEST_ONLY_changed_config!'):
            self.assertIsNone(self.lookup(credential).json()['data']['initial_password'])

    def test_rejected_request_cannot_be_supplemented_or_reset(self):
        credential=self.submit()['credential']
        self.assertEqual(self.handle(credential,'reject').json()['data']['status'],'rejected')
        self.assertEqual(self.client.post('/router/auth/recovery/supplement',json={'credential':credential,'content':'later'}).status_code,409)
        self.assertEqual(self.handle(credential).status_code,409)

    def test_ambiguous_or_missing_username_is_never_auto_reset(self):
        credential=self.submit('missing')['credential']
        self.assertEqual(self.handle(credential,'reset',identity_verified=True,target_user_id=20).status_code,400)
        with Session(self.engine) as db:
            db.add(User(username='reader',name='Duplicate',role='student',status=1,password=self.old_hash));db.commit()
        credential=self.submit()['credential']
        self.assertEqual(self.handle(credential,'reset',identity_verified=True,target_user_id=20).status_code,400)

    def test_privileged_or_disabled_account_protection_is_preserved(self):
        credential=self.submit('otheradmin')['credential']
        self.assertEqual(self.handle(credential,'reset',identity_verified=True,target_user_id=30).status_code,403)
        with Session(self.engine) as db:db.get(User,20).status=0;db.commit()
        credential=self.submit()['credential']
        result=self.handle(credential,'reset',identity_verified=True,target_user_id=20)
        self.assertNotEqual(result.json()['code'],200)
        self.assertEqual(self.lookup(credential).json()['data']['status'],'pending')

    def test_reset_refreshes_role_after_target_was_previously_loaded(self):
        from app.services import user_service
        with Session(self.engine) as stale:
            target=stale.get(User,20)
            self.assertEqual(target.role,'student')
            issuer=stale.get(User,10)
            with Session(self.engine) as fresh:
                fresh.get(User,20).role='admin';fresh.commit()
            with self.assertRaises(HTTPException) as error:
                user_service.reset_password(stale,20,issuer)
            self.assertEqual(error.exception.status_code,403)
            self.assertEqual(target.role,'admin')
        with Session(self.engine) as db:
            self.assertEqual(db.get(User,20).password,self.old_hash)

    def test_request_and_reset_are_atomic_when_commit_fails(self):
        credential=self.submit()['credential']
        with patch('sqlalchemy.orm.Session.commit',side_effect=RuntimeError('TEST_ONLY_ROLLBACK')):
            with self.assertRaises(RuntimeError):self.handle(credential,'reset',identity_verified=True,target_user_id=20)
        with Session(self.engine) as db:
            self.assertEqual(db.get(User,20).password,self.old_hash)
            self.assertEqual(db.get(RecoveryRequest,self.request_id(credential)).status,'pending')

    def test_same_username_submission_limit_and_query_limit(self):
        credential=self.submit()['credential'];self.submit();self.submit()
        result=self.client.post('/router/auth/recovery/requests',json={'username':'reader'})
        self.assertEqual(result.status_code,429)
        recovery_service.QUERY_BUCKETS.clear()
        for _ in range(30):self.assertEqual(self.lookup(credential).status_code,200)
        self.assertEqual(self.lookup(credential).status_code,429)

    def test_same_source_submission_limit_applies_across_usernames(self):
        for index in range(10):
            self.submit(f'unknown_{index}')
        response=self.client.post('/router/auth/recovery/requests',json={'username':'another_unknown'})
        self.assertEqual(response.status_code,429)
        with Session(self.engine) as db:
            self.assertEqual(db.query(RecoveryRequest).count(),10)

    def test_supplement_limit_and_invalid_input_does_not_echo_secret(self):
        credential=self.submit()['credential']
        for _ in range(5):
            self.assertEqual(self.client.post('/router/auth/recovery/supplement',json={'credential':credential,'content':'test'}).status_code,200)
        self.assertEqual(self.client.post('/router/auth/recovery/supplement',json={'credential':credential,'content':'test'}).status_code,429)
        response=self.client.post('/router/auth/recovery/supplement',json={'credential':credential,'content':'   '})
        self.assertEqual(response.status_code,422)
        self.assertNotIn(credential,response.text)

    def test_public_account_contact_endpoint_is_gone(self):
        self.assertEqual(self.client.get('/router/auth/contact').status_code,404)

if __name__=='__main__':unittest.main()
