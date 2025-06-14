from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from fastapi import Depends, HTTPException
from typing import Optional
from fastapi import Header
from fastapi.security import OAuth2PasswordBearer
from starlette.status import HTTP_401_UNAUTHORIZED
from .database import SessionLocal
from .models import User

# ✅ 관리자 이메일 리스트
ADMIN_EMAILS = ["alohad0han@gmail.com"]  # 👉 여기에 네 이메일 넣어

# ✅ .env에서 불러올 값들 (load_dotenv()는 main.py에서 이미 실행했다고 가정)
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7일간 유효한 토큰

# ✅ OAuth2PasswordBearer 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/google/jwt-login")

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()

    # ✅ 필수: sub(user_id)가 없으면 오류 발생
    if "sub" not in to_encode:
        raise ValueError("JWT payload must include 'sub' (user_id)")

    # ✅ 관리자 여부를 JWT에 포함
    user_email = to_encode.get("email")
    to_encode["is_admin"] = user_email in ADMIN_EMAILS

    # ✅ 만료 시간 설정
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})

    # ✅ JWT 생성 및 반환
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> Optional[dict]:
    """토큰 검증 로직만 수행"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except Exception as e:
        return None

def get_current_user(token: str = Depends(oauth2_scheme)):
    print("🔧 [get_current_user] 호출됨")  # 디버깅용 로그
    print("🔧 [get_current_user] 전달된 토큰:", token)

    payload = verify_token(token)
    if not payload:
        print("❌ [get_current_user] JWT 검증 실패")  # 디버깅용 로그
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    print("✅ [get_current_user] JWT payload:", payload)  # 디버깅용 로그
    return payload

def get_current_admin_user(token: str = Depends(oauth2_scheme)):
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="토큰 검증 실패")

    email = payload.get("email")
    if not email or email not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="관리자 권한이 없습니다.")

    # ✅ 실제 유저 존재 여부 확인 (선택적 보완)
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    db.close()

    if not user:
        raise HTTPException(status_code=403, detail="관리자 계정이 존재하지 않습니다.")

    return payload

def get_user_id_from_token(token: str) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub", "")
    except jwt.PyJWTError:
        return ""