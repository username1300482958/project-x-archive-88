from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# MySQL 연결 정보 (내비밀번호를 실제 비밀번호로 변경)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("❌ DATABASE_URL is not set in environment variables")

engine = create_engine(
    DATABASE_URL, 
    pool_recycle=1800, 
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ 바로 이 부분이 필요합니다
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()