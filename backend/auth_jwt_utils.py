from datetime import datetime, timedelta
from jose import JWTError, jwt
import os
from fastapi import Depends, HTTPException
from typing import Optional
from fastapi import Header
from fastapi.security import OAuth2PasswordBearer
from starlette.status import HTTP_401_UNAUTHORIZED
from .database import SessionLocal, get_db
from .models import User
from sqlalchemy.orm import Session

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
    
# ===================================================================
# 👇 [추가] 모든 API를 위한 '요금제 확인 전문가' 의존성 함수
# ===================================================================

# 👉 여기에 본인의 구글 ID (sub)를 문자열로 입력하세요.
# 예: YOUR_DEVELOPER_USER_ID = "10293847561234567890"
YOUR_DEVELOPER_USER_ID = "104120949912979219868"

def get_user_with_plan(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> User:
    """
    모든 API에서 일관된 방식으로 사용자 객체와 요금제를 가져오는 의존성 함수.
    관리자/개발자 계정일 경우, DB 정보 대신 ENTERPRISE 플랜을 적용한 가상 객체를 반환.
    """
    # 권한 확인: 요청된 user_id가 토큰의 주인과 일치하는지 확인
    # (단, 관리자는 모든 사용자의 정보를 볼 수 있도록 허용 - 이 부분은 필요에 따라 조정)
    if not current_user.get("is_admin") and current_user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="요청 권한이 없습니다.")
    
    # 관리자 또는 개발자 계정인지 확인
    is_admin = current_user.get("is_admin")
    is_developer = (user_id == YOUR_DEVELOPER_USER_ID)

    if is_admin or is_developer:
        print(f"🟢 'get_user_with_plan': 개발자({YOUR_DEVELOPER_USER_ID}) 또는 관리자 계정 확인. 가상 ENTERPRISE 유저 반환")
        # DB를 조회하지 않고, 'ENTERPRISE' 플랜을 가진 가상 User 객체를 만들어 반환
        virtual_user = User(
            id=user_id,
            plan="ENTERPRISE",
            username=current_user.get("username", "admin_user"),
            email=current_user.get("email", "admin@example.com"),
        )
        return virtual_user
    
    # 일반 사용자의 경우, 데이터베이스에서 조회
    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    return user_obj
