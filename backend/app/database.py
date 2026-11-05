from sqlalchemy.orm import sessionmaker,DeclarativeBase,Mapped,mapped_column
from sqlalchemy import create_engine,DateTime,inspect,text
from app.config import settings
from datetime import datetime

engine = create_engine(
    settings.DATABASE_URL
)


SessionLocal = sessionmaker(
    bind= engine,
    autoflush=False
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Base(DeclarativeBase):
    id:Mapped[int] = mapped_column(primary_key = True,autoincrement=True,comment="主键ID")
    create_time: Mapped[datetime] =  mapped_column(DateTime,default=datetime.now,comment="创建时间")
    update_time: Mapped[datetime] =  mapped_column(DateTime,default=datetime.now,onupdate=datetime.now, comment="更新时间")


def initialize_database(database_engine=engine):
    Base.metadata.create_all(bind=database_engine)
    columns = inspect(database_engine).get_columns('users')
    if not any(column['name'] == 'must_change_password' for column in columns):
        with database_engine.begin() as connection:
            connection.execute(text('ALTER TABLE users ADD COLUMN must_change_password BOOLEAN NOT NULL DEFAULT 0'))




