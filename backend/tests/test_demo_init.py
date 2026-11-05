"""演示初始化安全边界：只使用内存SQLite，不连接真实MySQL。"""
import sys
import unittest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from init_demo import check_demo_database,create_demo_data
from app.database import Base
from app.models.user import User
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.utils.password import verify_password


class DemoInitTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)

    def test_only_named_mysql_demo_database_is_allowed(self):
        check_demo_database('mysql+pymysql://demo@localhost/labflow_demo')
        for value in ['mysql+pymysql://demo@localhost/lab_agent','mysql+pymysql://demo@localhost/production','sqlite://']:
            with self.assertRaises(ValueError):check_demo_database(value)

    def test_seed_hashes_passwords_and_only_contains_fictional_empty_resources(self):
        with Session(self.engine) as db:
            result = create_demo_data(db,'TEST_ONLY_admin_password!','TEST_ONLY_student_password!')
            self.assertEqual((result['labs'],result['equipments']),(3,3))
            admin = db.query(User).filter_by(username='demo_admin').one()
            self.assertEqual(admin.role,'admin')
            self.assertTrue(verify_password('TEST_ONLY_admin_password!',admin.password))
            self.assertIsNone(admin.email)
            self.assertEqual(db.query(Lab).count(),3)
            self.assertEqual(db.query(Equipment).count(),3)
            original = admin.password
            with self.assertRaises(ValueError):create_demo_data(db,'TEST_ONLY_new_admin!','TEST_ONLY_new_student!')
            self.assertEqual(admin.password,original)
            self.assertEqual(db.query(User).count(),2)

    def test_existing_database_is_never_partially_seeded(self):
        with Session(self.engine) as db:
            db.add(Lab(name='Existing',capacity=1,open_time='08:00',close_time='17:00',status='1'))
            db.commit()
            with self.assertRaises(ValueError):create_demo_data(db,'TEST_ONLY_admin_password!','TEST_ONLY_student_password!')
            self.assertEqual(db.query(User).count(),0)
            self.assertEqual(db.query(Lab).count(),1)

    def test_invalid_password_does_not_create_accounts(self):
        with Session(self.engine) as db:
            with self.assertRaises(ValueError):create_demo_data(db,'short','TEST_ONLY_student_password!')
            self.assertEqual(db.query(User).count(),0)


if __name__ == '__main__':unittest.main()
