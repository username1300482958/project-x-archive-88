import os
import requests
from fastapi import APIRouter, Request, HTTPException, Depends
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from backend.auth_jwt_utils import create_access_token
from backend.database import get_db
from backend.models import User
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

@router.get("/auth/google/redirect")
def redirect_login_to_google():
    """
    브라우저에서 window.location.href = BACKEND_URL + '/auth/google/redirect'
    형태로 호출 시, 구글 로그인 페이지로 직접 Redirect 시켜 줍니다.
    """
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": REDIRECT_URI,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{google_auth_url}?{urlencode(params)}"
    return RedirectResponse(url=auth_url)

@router.get("/auth/google")
def get_google_auth_url():
    """
    fetch 호출 시 JSON으로 auth_url을 반환합니다.
    프론트에서 fetch('/auth/google').then(res => res.json()).then(data => window.location.href = data.auth_url) 형태로 사용하세요.
    """
    google_auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": REDIRECT_URI,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{google_auth_url}?{urlencode(params)}"
    return JSONResponse(content={"auth_url": auth_url})

@router.get("/auth/google/callback")
@router.get("/auth/google/callback/")
def google_callback(
    request: Request,
    code: str,
    db: Session = Depends(get_db),
):
    """
    구글이 이 URL로 리디렉션할 때 code를 받아서,
    토큰 발급 → 유저 확인/등록 → JWT 발급 → JSON 응답으로 반환합니다.
    """
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code missing")

    # 1. Google에 access_token 요청
    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    token_resp = requests.post(token_url, data=data)
    token_json = token_resp.json()
    if token_json.get("error"):
        raise HTTPException(
            status_code=401,
            detail=f"Google token error: {token_json.get('error_description')}",
        )

    access_token = token_json.get("access_token")
    if not access_token:
        raise HTTPException(status_code=401, detail="Google access token missing")

    # 2. 구글 유저 정보 조회
    userinfo_resp = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_info = userinfo_resp.json()
    user_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name") or user_id
    if not user_id:
        raise HTTPException(status_code=401, detail="Google user ID not found")

    # 3. DB에 유저 저장 또는 병합
    try:
        print("✅ user_info:", user_info)  # 이 줄 추가
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            same_email = db.query(User).filter(User.email == email).first()
            print("✅ same_email:", same_email)  # 이 줄 추가
            if same_email:
                same_email.id = user_id
                same_email.name = name
                same_email.email = email
                db.flush()
            else:
                user = User(id=user_id, username=user_id, email=email, name=name)
                db.add(user)
        db.commit()
    except Exception as e:
        db.rollback()
        print("❌ DB 예외:", e)  # 이 줄 추가
        raise HTTPException(status_code=500, detail=f"DB 처리 중 오류 발생: {e}")

    # 4. JWT 발급
    jwt_token = create_access_token({"sub": user_id, "email": email, "name": name})

    # 5. JSON 응답으로 반환
    return {
        "access_token": jwt_token,
        "user_id": user_id,
        "email": email,
    }