from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    DECIMAL,
    Enum,
    TIMESTAMP,
    text,
)
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

# 사용자 테이블
class User(Base):
    __tablename__ = "users"
    id = Column(String(255), primary_key=True, index=True)  # ✅ 수정됨
    username = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    plan = Column(String(20), default="FREE")
    plan_changed_at = Column(DateTime, default=datetime.utcnow)  # ✅ 추가됨
    admin = Column(Boolean, default=False)

# 로고 테이블
class Logo(Base):
    __tablename__ = "logos"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ✅ 수정됨
    logo_path = Column(String(500), nullable=False)
    # 추가된 컬럼들:
    s3_url = Column(String(500), nullable=False, default="")
    brand_name = Column(String(255), nullable=False)
    logo_style = Column(String(100), nullable=False)
    colors = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    s3_uploaded = Column(Boolean, nullable=False, default=False)
    s3_uploaded_at = Column(TIMESTAMP, nullable=True)

# Favorite 테이블 (추가)
class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ✅ 수정됨
    logo_id = Column(Integer, ForeignKey("logos.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

# 결제 테이블
class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ✅ 수정됨
    logo_id = Column(Integer, ForeignKey("logos.id", ondelete="CASCADE"), nullable=False)
    amount = Column(DECIMAL(10, 2), nullable=False)
    status = Column(Enum("pending", "completed", "failed"), default="pending")
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

# 다운로드 기록 테이블
class Download(Base):
    __tablename__ = "downloads"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)  # ✅ 수정됨
    logo_id = Column(Integer, ForeignKey("logos.id", ondelete="CASCADE"), nullable=False)
    downloaded_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))
    # ✅ 개선된 필드들
    download_type = Column(Enum("free", "paid", name="download_type_enum"), nullable=False, default="free")
    status = Column(Enum("success", "failed", name="download_status_enum"), nullable=False, default="success")
    attempts = Column(Integer, default=1)
    error_message = Column(String(500), nullable=True)

# 에러 로그 테이블
class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)  # ✅ 수정됨
    context = Column(String(255), nullable=False)  # 예: "S3 Upload", "LogoGeneration"
    message = Column(String(1000), nullable=False)
    stack_trace = Column(String(2000), nullable=True)
    created_at = Column(TIMESTAMP, server_default=text("CURRENT_TIMESTAMP"))

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(String(255), unique=True, index=True)
    user_id = Column(String(255), index=True)
    plan_id = Column(String(255))
    logo_id = Column(String(255), nullable=True)
    status = Column(String(255), default="pending")  # pending / paid / failed
    created_at = Column(DateTime, default=datetime.utcnow)