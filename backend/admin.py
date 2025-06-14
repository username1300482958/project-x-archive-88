from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import User, Logo
from backend.auth_jwt_utils import verify_token
from backend.auth_jwt_utils import create_access_token

router = APIRouter(
    prefix="/admin",
    tags=["admin"]
)

# ✅ DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ 관리자 인증 의존성
def get_current_admin_user(token_payload: dict = Depends(verify_token)):
    if token_payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")
    return token_payload

# ✅ 전체 사용자 조회 (관리자 전용)
@router.get("/users")
def get_all_users(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    return db.query(User).all()

# ✅ 전체 로고 조회 (관리자 전용)
@router.get("/logos")
def get_all_logos(
    db: Session = Depends(get_db),
    admin_user=Depends(get_current_admin_user)
):
    return db.query(Logo).all()

# ✅ 관리자 테스트 토큰 발급용 (개발 전용)
@router.post("/test-generate-token")
def generate_admin_token():
    token = create_access_token({
        "sub": "test_admin",
        "email": "admin@example.com",
        "role": "admin"  # ✅ 반드시 role 명시
    })
    return {"token": token}