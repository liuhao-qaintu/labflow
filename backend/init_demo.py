"""初始化空的 labflow_demo 数据库；不覆盖现有数据、不保存明文演示密码。"""
import argparse
from getpass import getpass
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal,initialize_database
from app.models.user import User
from app.models.lab import Lab
from app.models.equipment import Equipment
from app.models.reservation import Reservation
from app.models.recovery import RecoveryRequest,RecoveryEvent
from app.utils.password import hash_password


def check_demo_database(database_url):
    url = make_url(database_url)
    if url.get_backend_name() != 'mysql' or url.database != 'labflow_demo':
        raise ValueError('初始化只允许MySQL的labflow_demo数据库，请使用独立的演示配置')


def create_demo_data(db:Session,admin_password:str,student_password:str):
    for password in (admin_password,student_password):
        if len(password) < 8 or len(password.encode('utf-8')) > 72:
            raise ValueError('演示密码至少8个字符，且不超过72个UTF-8字节')
    for model in (User,Lab,Equipment,Reservation,RecoveryRequest,RecoveryEvent):
        if db.query(model).first():
            raise ValueError('数据库已有数据，初始化已取消；不会覆盖账号、密码或预约')
    admin = User(username='demo_admin',name='演示管理员',role='admin',status=1,password=hash_password(admin_password))
    student = User(username='demo_student',name='演示学生',role='student',status=1,password=hash_password(student_password))
    db.add_all([admin,student])
    labs = [Lab(name='计算机实验室',description='虚构演示资源，可用于设备查询和预约。',capacity=20,open_time='08:00',close_time='21:00',location='演示楼A101',img=None,status='1'),
            Lab(name='化学实验室',description='虚构演示资源，操作前应遵守安全规范。',capacity=12,open_time='08:30',close_time='18:00',location='演示楼B201',img=None,status='1'),
            Lab(name='物理实验室',description='虚构演示资源，用于仪器预约演示。',capacity=16,open_time='08:00',close_time='20:00',location='演示楼C301',img=None,status='1')]
    db.add_all(labs)
    db.flush()
    db.add_all([Equipment(lab_id=labs[0].id,name='GPU工作站',description='虚构演示设备。',spec='演示型号A',quantity=1,status='1'),
                Equipment(lab_id=labs[1].id,name='分析天平',description='虚构演示设备。',spec='演示型号B',quantity=1,status='1'),
                Equipment(lab_id=labs[2].id,name='电子显微镜',description='虚构演示设备。',spec='演示型号C',quantity=1,status='1')])
    db.commit()
    return {'admin_id':admin.id,'student_id':student.id,'labs':len(labs),'equipments':3}


def read_password(label):
    password = getpass(label)
    if password != getpass('再次输入：'):
        raise ValueError('两次输入不一致，初始化已取消')
    return password


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-demo-database',required=True,choices=['labflow_demo'])
    parser.parse_args()
    check_demo_database(settings.DATABASE_URL)
    admin_password = read_password('设置demo_admin密码：')
    student_password = read_password('设置demo_student密码：')
    initialize_database()
    with SessionLocal() as db:
        result = create_demo_data(db,admin_password,student_password)
    print(f'已创建虚构演示数据：管理员ID={result["admin_id"]}，学生ID={result["student_id"]}，实验室3间，设备3台。')
    print('可在本地.env中把PASSWORD_RECOVERY_ADMIN_ID设为上述管理员ID。维护白名单默认仍关闭。')


if __name__ == '__main__':
    try:
        main()
    except ValueError as error:
        raise SystemExit(str(error))
