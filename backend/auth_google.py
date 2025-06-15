import os
import requests
import traceback  # 디버깅을 위한 traceback 모듈 추가
from fastapi import APIRouter, Request, HTTPException, Depends
from urllib.parse import urlencode
from sqlalchemy.orm import Session
from .auth_jwt_utils import create_access_token
from .database import get_db
from .models import User
from starlette.responses import RedirectResponse
from fastapi.responses import JSONResponse

router = APIRouter()

# 이 부분은 그대로 둡니다.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# ==============================================================================
# 아래의 모든 함수에 디버깅용 try...except 구문과 print 로그를 추가했습니다.
# ==============================================================================

@router.get("/auth/google/redirect")
def redirect_login_to_google():
    """
    브라우저에서 직접 호출 시, 구글 로그인 페이지로 Redirect 시켜 줍니다.
    """
    print("--- ✅ /auth/google/redirect API가 호출되었습니다. ---")
    try:
        # 환경 변수가 제대로 로드되었는지 확인 (가장 중요한 부분)
        if not GOOGLE_CLIENT_ID or not REDIRECT_URI:
            print("--- 🚨 치명적 오류: GOOGLE_CLIENT_ID 또는 REDIRECT_URI 환경 변수가 설정되지 않았습니다! ---")
            raise ValueError("Google OAuth 환경 변수가 설정되지 않았습니다.")
        
        print(f"--- ⚙️ 환경 변수 확인 완료. GOOGLE_CLIENT_ID: {'설정됨' if GOOGLE_CLIENT_ID else '누락됨'}")

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
        
        print("--- ✅ 성공: 구글 인증 Redirect URL 생성을 완료했습니다. ---")
        return RedirectResponse(url=auth_url)

    except Exception as e:
        print("--- 🚨🚨🚨 /auth/google/redirect API 실행 중 심각한 오류 발생! 🚨🚨🚨 ---")
        print(f"--- 오류 타입: {type(e)}")
        print(f"--- 오류 내용: {e}")
        print("--- 오류 상세 Traceback ---")
        traceback.print_exc()
        print("--------------------------")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")


@router.get("/auth/google")
def get_google_auth_url():
    """
    프론트엔드에서 fetch 호출 시 JSON으로 auth_url을 반환합니다. (현재 문제가 되는 부분)
    """
    print("--- ✅ /auth/google API가 호출되었습니다. ---")
    try:
        # 환경 변수가 제대로 로드되었는지 확인 (가장 중요한 부분)
        if not GOOGLE_CLIENT_ID or not REDIRECT_URI:
            print("--- 🚨 치명적 오류: GOOGLE_CLIENT_ID 또는 REDIRECT_URI 환경 변수가 설정되지 않았습니다! ---")
            raise ValueError("Google OAuth 환경 변수가 설정되지 않았습니다.")
        
        print(f"--- ⚙️ 환경 변수 확인 완료. GOOGLE_CLIENT_ID: {'설정됨' if GOOGLE_CLIENT_ID else '누락됨'}")

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

        print("--- ✅ 성공: 구글 인증 URL 생성을 완료했습니다. ---")
        return JSONResponse(content={"auth_url": auth_url})

    except Exception as e:
        print("--- 🚨🚨🚨 /auth/google API 실행 중 심각한 오류 발생! 🚨🚨🚨 ---")
        print(f"--- 오류 타입: {type(e)}")
        print(f"--- 오류 내용: {e}")
        print("--- 오류 상세 Traceback ---")
        traceback.print_exc()
        print("--------------------------")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")


@router.get("/auth/google/callback")
@router.get("/auth/google/callback/")
def google_callback(request: Request, code: str, db: Session = Depends(get_db)):
    """
    구글 로그인 후 리디렉션되는 URL. 안정성 강화를 위해 디버깅 코드 추가.
    """
    print("--- ✅ /auth/google/callback API가 호출되었습니다. ---")
    try:
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code missing")

        # 1. Google에 access_token 요청
        print("--- ⚙️ 구글에 access_token을 요청합니다. ---")
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
            print(f"--- 🚨 구글 토큰 에러: {token_json.get('error_description')} ---")
            raise HTTPException(
                status_code=401,
                detail=f"Google token error: {token_json.get('error_description')}",
            )

        access_token = token_json.get("access_token")
        if not access_token:
            raise HTTPException(status_code=401, detail="Google access token missing")

        # 2. 구글 유저 정보 조회
        print("--- ⚙️ 구글 유저 정보를 조회합니다. ---")
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
        print("--- ⚙️ DB 작업을 시작합니다. ---")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            same_email = db.query(User).filter(User.email == email).first()
            if same_email:
                same_email.id = user_id
                same_email.name = name
                same_email.email = email
                db.flush()
            else:
                user = User(id=user_id, username=user_id, email=email, name=name)
                db.add(user)
        db.commit()
        print("--- ✅ DB 작업 완료. ---")

        # 4. JWT 발급
        jwt_token = create_access_token({"sub": user_id, "email": email, "name": name})

        # 5. JSON 응답으로 반환
        return { "access_token": jwt_token, "user_id": user_id, "email": email }

    except Exception as e:
        db.rollback()
        print("--- 🚨🚨🚨 /auth/google/callback API 실행 중 심각한 오류 발생! 🚨🚨🚨 ---")
        print(f"--- 오류 타입: {type(e)}")
        print(f"--- 오류 내용: {e}")
        print("--- 오류 상세 Traceback ---")
        traceback.print_exc()
        print("--------------------------")
        raise HTTPException(status_code=500, detail="서버 내부 오류가 발생했습니다.")