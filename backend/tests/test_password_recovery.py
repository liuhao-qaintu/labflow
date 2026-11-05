"""管理员重置及强制改密：只使用内存数据库和测试签名，不改真实账号。"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.common.exceptions import BusinessException, business_exception_handler, http_exception_handler, validation_exception_handler
from app.config import settings
from app.database import Base, get_db, initialize_database
from app.models.user import User
from app.router import router
from app.utils.jwt import create_access_token
from app.utils.password import hash_password, verify_password

OLD = 'TEST_ONLY_OldPassword_123!'
INITIAL = 'TEST_ONLY_InitialPassword_456!'
NEW = 'TEST_ONLY_NewPassword_789!'
KEY = 'TEST_ONLY_fake_signing_key_never_used_by_live_service'


class PasswordRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_hash = hash_password(OLD)

    def setUp(self):
        self.engine = create_engine('sqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            db.add_all([User(id=10, username='admin', name='Admin', role='admin', status=1, password=self.old_hash),
                        User(id=20, username='reader', name='Reader', role='student', status=1, password=self.old_hash),
                        User(id=30, username='other', name='Other', role='student', status=1, password=self.old_hash),
                        User(id=40, username='maintainer', name='Maintainer', role='admin', status=1, password=self.old_hash)])
            db.commit()
        for name, value in [('JWT_SECRET_KEY', KEY), ('DEVELOPER_USER_IDS', [40]),
                            ('RESET_INITIAL_PASSWORD', INITIAL)]:
            option = patch.object(settings, name, value)
            option.start()
            self.addCleanup(option.stop)
        self.app = FastAPI()
        self.app.include_router(router)
        self.app.add_exception_handler(BusinessException, business_exception_handler)
        self.app.add_exception_handler(HTTPException, http_exception_handler)
        self.app.add_exception_handler(RequestValidationError, validation_exception_handler)
        def database():
            with Session(self.engine) as db:
                yield db
        self.app.dependency_overrides[get_db] = database
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.addCleanup(self.engine.dispose)

    def headers(self, uid=10):
        with Session(self.engine) as db:
            token = create_access_token(uid, db.get(User, uid).password)
        return {'Authorization':'Bearer ' + token}

    def reset(self, uid=20, issuer=10, **payload):
        return self.client.put(f'/router/user/{uid}/password/reset', headers=self.headers(issuer),
                               json={'identity_verified':True, **payload})

    def initial_login(self):
        result = self.client.post('/router/auth/login', json={'username':'reader', 'password':INITIAL})
        self.assertEqual(result.json()['code'], 200)
        self.assertTrue(result.json()['data']['user']['must_change_password'])
        return {'Authorization':'Bearer ' + result.json()['data']['token']}

    def test_public_contact_email_endpoint_is_removed(self):
        self.assertEqual(self.client.get('/router/auth/contact').status_code,404)

    def test_anonymous_and_student_cannot_reset(self):
        path = '/router/user/20/password/reset'
        self.assertEqual(self.client.put(path, json={'identity_verified':True}).status_code, 401)
        self.assertEqual(self.reset(30, 20).status_code, 403)

    def test_explicit_verification_is_required_and_extra_fields_rejected(self):
        for payload in ({}, {'identity_verified':False}, {'identity_verified':True, 'password':INITIAL}):
            result = self.client.put('/router/user/20/password/reset', headers=self.headers(), json=payload)
            self.assertEqual(result.status_code, 422)
            self.assertNotIn(INITIAL, result.text)
        with Session(self.engine) as db:
            self.assertEqual(db.get(User, 20).password, self.old_hash)

    def test_reset_only_changes_target_password_and_flag(self):
        old_headers = self.headers(20)
        result = self.reset()
        self.assertEqual(result.json()['code'], 200)
        self.assertNotIn(INITIAL, result.text)
        self.assertNotIn('password', result.json().get('data') or {})
        with Session(self.engine) as db:
            user = db.get(User, 20)
            self.assertTrue(verify_password(INITIAL, user.password))
            self.assertNotEqual(user.password, INITIAL)
            self.assertEqual((user.role, user.status, user.must_change_password), ('student',1,True))
            self.assertEqual(db.get(User, 30).password, self.old_hash)
        self.assertEqual(self.client.get('/router/user/me', headers=old_headers).status_code, 401)
        login = self.client.post('/router/auth/login', json={'username':'reader', 'password':OLD})
        self.assertNotEqual(login.json()['code'], 200)

    def test_admin_cannot_reset_admin_or_maintainer(self):
        for uid in (10,40):
            self.assertEqual(self.reset(uid).status_code, 403)

    def test_maintainer_can_reset_admin_after_verification(self):
        self.assertEqual(self.reset(10,40).json()['code'], 200)
        with Session(self.engine) as db:
            self.assertTrue(db.get(User,10).must_change_password)

    def test_downgraded_maintainer_is_still_protected(self):
        with Session(self.engine) as db:
            db.get(User,40).role = 'student'
            db.commit()
        self.assertEqual(self.reset(40).status_code, 403)
        rows = self.client.get('/router/user/list', headers=self.headers()).json()['data']['list']
        self.assertFalse(next(row for row in rows if row['id']==40)['can_reset_password'])

    def test_missing_and_disabled_users_are_not_reset_or_reenabled(self):
        with Session(self.engine) as db:
            db.get(User,20).status = 0
            db.commit()
        for uid in (20,999):
            self.assertNotEqual(self.reset(uid).json()['code'], 200)
        with Session(self.engine) as db:
            self.assertEqual((db.get(User,20).status, db.get(User,20).password), (0,self.old_hash))

    def test_missing_initial_password_configuration_fails_without_changes(self):
        for value in ('', 'short', '中'*25):
            with patch.object(settings, 'RESET_INITIAL_PASSWORD', value):
                self.assertNotEqual(self.reset().json()['code'], 200)
        with Session(self.engine) as db:
            self.assertFalse(db.get(User,20).must_change_password)
            self.assertEqual(db.get(User,20).password, self.old_hash)

    def test_initial_login_can_read_own_identity_but_cannot_use_business_endpoints(self):
        self.reset()
        headers = self.initial_login()
        self.assertEqual(self.client.get('/router/user/me', headers=headers).status_code, 200)
        for path in ('/router/lab/list','/router/equipment/list','/router/reservation/list','/router/user/list'):
            self.assertEqual(self.client.get(path, headers=headers).status_code, 428, path)
        for path in ('/router/ai/chat','/router/ai/chat/stream'):
            result = self.client.post(path, headers=headers, json={'messages':[{'role':'user','content':'测试'}]})
            self.assertEqual(result.status_code, 428, path)
        result = self.client.post('/router/files/upload', headers=headers, files={'file':('test.png',b'no write')})
        self.assertEqual(result.status_code, 428)
        self.assertEqual(self.client.put('/router/user/me',headers=headers,json={'name':'bypass','must_change_password':False}).status_code,428)

    def test_change_password_clears_flag_revokes_temporary_login_and_restores_business(self):
        self.reset()
        headers = self.initial_login()
        response = self.client.put('/router/user/password',headers=headers,json={'old_password':INITIAL,'new_password':NEW})
        self.assertEqual(response.json()['code'],200)
        self.assertEqual(self.client.get('/router/user/me',headers=headers).status_code,401)
        login = self.client.post('/router/auth/login',json={'username':'reader','password':NEW}).json()
        self.assertEqual(login['code'],200)
        self.assertFalse(login['data']['user']['must_change_password'])
        result = self.client.get('/router/reservation/list',headers={'Authorization':'Bearer '+login['data']['token']})
        self.assertEqual(result.json()['code'],200)

    def test_wrong_old_password_weak_or_unchanged_new_password_cannot_clear_flag(self):
        self.reset()
        headers = self.headers(20)
        for old,new in ((OLD,NEW),(INITIAL,'123'),(INITIAL,INITIAL),(INITIAL,'中'*25)):
            response = self.client.put('/router/user/password',headers=headers,json={'old_password':old,'new_password':new})
            self.assertNotEqual(response.json()['code'],200)
            self.assertNotIn(new,response.text)
        with Session(self.engine) as db:
            self.assertTrue(db.get(User,20).must_change_password)

    def test_repeated_reset_revokes_prior_temporary_token(self):
        self.reset()
        temporary = self.headers(20)
        self.reset()
        self.assertEqual(self.client.get('/router/user/me',headers=temporary).status_code,401)

    def test_flag_survives_new_session_and_ignores_claim_in_jwt(self):
        self.reset()
        with Session(self.engine) as db:
            self.assertTrue(db.get(User,20).must_change_password)
        import jwt
        token = self.headers(20)['Authorization'].split(' ',1)[1]
        payload = jwt.decode(token, KEY, algorithms=['HS256'])
        payload['must_change_password'] = False
        token = jwt.encode(payload, KEY, algorithm='HS256')
        self.assertEqual(self.client.get('/router/reservation/list',headers={'Authorization':'Bearer '+token}).status_code,428)

    def test_forced_change_also_blocks_an_admin_from_resetting_someone_else(self):
        self.reset(10,40)
        response = self.reset(20,10)
        self.assertEqual(response.status_code,428)
        with Session(self.engine) as db:
            self.assertEqual(db.get(User,20).password,self.old_hash)

    def test_old_link_endpoints_no_longer_exist(self):
        for method,path in (('post','/router/auth/password-reset'),('post','/router/auth/users/20/password-reset'),('get','/router/auth/password-reset/permissions')):
            self.assertEqual(getattr(self.client,method)(path,headers=self.headers()).status_code,404)

    def test_list_reset_buttons_reflect_server_permissions(self):
        rows = self.client.get('/router/user/list',headers=self.headers()).json()['data']['list']
        self.assertEqual({row['id']:row['can_reset_password'] for row in rows}, {10:False,20:True,30:True,40:False})
        self.assertTrue(all('password' not in row for row in rows))

    def test_changed_password_invalidates_legacy_and_missing_version_tokens(self):
        import jwt
        token = jwt.encode({'user_id':20}, KEY, algorithm='HS256')
        self.assertEqual(self.client.get('/router/user/me',headers={'Authorization':'Bearer '+token}).status_code,401)


class DatabaseMigrationTests(unittest.TestCase):
    def test_existing_database_adds_flag_once_and_keeps_existing_data(self):
        engine = create_engine('sqlite://')
        self.addCleanup(engine.dispose)
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, password VARCHAR(255))'))
            connection.execute(text("INSERT INTO users (id,password) VALUES (1,'unchanged-test-hash')"))
        initialize_database(engine)
        initialize_database(engine)
        self.assertEqual([c['name'] for c in inspect(engine).get_columns('users')].count('must_change_password'),1)
        with engine.connect() as connection:
            self.assertEqual(tuple(connection.execute(text('SELECT password,must_change_password FROM users')).one()),('unchanged-test-hash',0))


if __name__ == '__main__':
    unittest.main()
