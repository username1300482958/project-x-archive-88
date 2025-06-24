# --- Python 기본 라이브러리 ---
import os
import smtplib
import uuid
import random
import logging
import shutil
import re
import traceback
import inspect
from email.mime.text import MIMEText
from email.header import Header as EmailHeader
from datetime import datetime, timedelta
from typing import List, Optional, Union

# --- 서드파티 라이브러리 (FastAPI, SQLAlchemy 등) ---
from fastapi import FastAPI, HTTPException, Query, Depends, Request, Header, APIRouter, Form
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi_utils.tasks import repeat_every
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# --- 로컬 모듈 (직접 작성한 코드) ---
# .env 파일 로드 (가장 먼저 실행되도록 위로 이동)
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

from .database import SessionLocal, engine, Base, get_db
from . import models
from .schemas import BulkDeleteRequest
from .utils import get_client_ip, log_error
from .utils_watermark import apply_rotated_watermark
from .s3_utils import upload_to_s3, generate_presigned_url_from_s3_url, delete_from_s3
from .s3_cleanup import clean_expired_s3_logos
from .openai_utils import generate_logo_image
from .logo_prompt_optimizer import generate_prompt_with_gpt
from .auth_jwt_utils import get_current_user, get_user_with_plan, verify_token
from .config import BASE_BACKEND_URL

# 라우터 import
from . import admin
from .auth_jwt import router as jwt_auth_router
from .auth_google import router as google_auth_router
from .payments import router as payment_router
from .downloads import router as downloads_router
from .download_upscaled import router as download_upscaled_router
from .favorites import router as favorites_router


# --- FastAPI 앱 초기화 및 설정 ---
app = FastAPI()
app.include_router(google_auth_router)
# --- 최종 디버깅 및 강제 등록 코드 ---
from .auth_google import get_google_auth_url

# 현재 앱에 등록된 모든 라우트를 출력해서 확인합니다.
@app.on_event("startup")
def print_all_routes():
    print("--- 등록된 모든 API 라우트 ---")
    for route in app.routes:
        if hasattr(route, "methods"):
            print(f"Path: {route.path}, Methods: {route.methods}, Name: {route.name}")
    print("--------------------------")

# 문제가 되는 라우트를 수동으로, 직접, 강제로 등록합니다.
app.add_api_route(
    "/auth/google",
    get_google_auth_url,
    methods=["GET"],
    name="get_google_auth_url_manual"
)
# --- 여기까지 ---

# --- 👇 여기에 추가합니다 ---
models.Base.metadata.create_all(bind=engine)
# --- 👆 여기까지 ---

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "https://brandieai.com",
        "https://www.brandieai.com",
        "https://youthful-side-183046.framer.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 예외 처리 핸들러 ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logging.exception("❌ 처리되지 않은 예외 발생:")
    return PlainTextResponse(content="서버 내부 오류가 발생했습니다.", status_code=500)

# ✅ 수정된 예외 처리 핸들러: 안정성 강화
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    print(f"❌ [422] 요청 유효성 검증 실패: {errors}")

    # JSON으로 변환 가능한 안전한 정보만 추출하여 새로운 리스트를 만듭니다.
    # 이렇게 하면 'bytes' 같은 타입 때문에 서버가 다운되는 현상을 막을 수 있습니다.
    response_errors = []
    for error in errors:
        response_errors.append({
            "type": error.get("type"),
            "loc": error.get("loc"),
            "msg": error.get("msg"),
        })

    return JSONResponse(
        status_code=422,
        content={"detail": response_errors},
    )
# ✅ 여기까지가 수정된 부분입니다.


# --- 상수 및 설정값 ---
PLAN_CONFIG = {
    "FREE": {"max_total": 1, "max_batch": 1, "max_download": 0, "s3_retention_days": 30},
    "STARTER": {"max_total": 10, "max_batch": 10, "max_download": 3, "s3_retention_days": 90},
    "BASIC": {"max_total": 10, "max_batch": 10, "max_download": 3, "s3_retention_days": 90},
    "PRO": {"max_total": 20, "max_batch": 20, "max_download": 10, "s3_retention_days": 180},
    "ENTERPRISE": {"max_total": 50, "max_batch": 50, "max_download": 20, "s3_retention_days": 365}
}
BASE_LOGO_FOLDER = "generated_logos"
PAID_LOGO_FOLDER = "paid_logos"
os.makedirs(BASE_LOGO_FOLDER, exist_ok=True)
os.makedirs(PAID_LOGO_FOLDER, exist_ok=True)


# --- Pydantic 모델 정의 ---
class LogoRequest(BaseModel):
    user_id: str
    brand_name: str
    logo_style: str
    colors: List[str]
    font_style: Optional[str] = None
    batch_size: int = 1
    style_detail: Optional[str] = None
    background: Optional[str] = None
    core_object: Optional[str] = None

class ContactForm(BaseModel):
    name: str
    email: str
    message: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API 엔드포인트 ---
# [참고] 기존의 모든 엔드포인트(/contact, /generate-logo 등)는
# 변경 없이 그대로 유지되므로 여기서는 생략합니다.
# 사용자의 코드에서 이 부분은 그대로 두시면 됩니다.
@app.post("/contact")
def send_contact_message(form: ContactForm):
    subject = f"[문의] {form.name}님으로부터"
    body = f"이름: {form.name}\n이메일: {form.email}\n\n문의내용:\n{form.message}"

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = EmailHeader(subject, "utf-8")
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = os.getenv("TO_EMAIL")

    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
            server.sendmail(
                os.getenv("EMAIL_USER"),
                os.getenv("TO_EMAIL"),
                msg.as_string(),
            )
        return {"message": "메일 전송 완료"}
    except Exception as e:
        print("❌ 메일 전송 실패:", e)
        return {"error": "메일 전송 실패"}

@app.post("/generate-logo")
async def generate_logo(
    request: LogoRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
    req: Request = None
):
    print("🟡 generate_logo 진입")
    print("🟡 request.user_id:", request.user_id)
    print("🟡 request.brand_name:", request.brand_name)
    print("🟡 request.logo_style:", request.logo_style)
    print("🟡 request.colors:", request.colors)
    print("🟡 request.font_style:", request.font_style)
    print("🟡 request.batch_size:", request.batch_size)
    client_ip = get_client_ip(req)
    print(f"📡 요청자 IP: {client_ip}")

    # 🔒 권한검사
    if request.user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    
    # ✅ abuse 방지 필터링: 최근 3시간 이내 동일 IP에서 다른 FREE 계정 생성 기록 확인
    three_hours_ago = datetime.utcnow() - timedelta(hours=3)
    recent_free_user_ids = (
        db.query(models.User.id)
        .join(models.Logo, models.User.id == models.Logo.user_id)
        .filter(
            models.User.plan == "FREE",
            models.Logo.created_at >= three_hours_ago,
            models.Logo.user_id != request.user_id
        )
        .distinct()
        .all()
    )
    recent_user_ids = [row.id for row in recent_free_user_ids]

    if recent_user_ids:
        recent_ips = (
            db.query(models.ErrorLog.user_id, models.ErrorLog.message)
            .filter(
                models.ErrorLog.user_id.in_(recent_user_ids),
                models.ErrorLog.context == "AbuseCheck"
            )
            .all()
        )
        for uid, logged_ip in recent_ips:
            if logged_ip == client_ip:
                print(f"🚫 abuse 감지됨: IP={client_ip}, 다른 FREE 유저={uid}")
                raise HTTPException(status_code=429, detail="FREE 요금제는 동일 IP에서 일정 시간 내 중복 생성이 제한됩니다.")

    # ✅ IP 로깅 (비교용)
    log_error(user_id=request.user_id, context="AbuseCheck", message=client_ip)

    # ✅ 사용자 조회 또는 생성
    user_obj = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user_obj:
        user_obj = models.User(
            id=request.user_id,
            username=request.user_id,
            email=f"{request.user_id}@example.com",
            plan="FREE"  # 신규 가입 시 FREE로 지정
        )
        db.add(user_obj)
        db.commit()
        db.refresh(user_obj)

    plan = (user_obj.plan or "FREE").upper()
    limits = PLAN_CONFIG.get(plan, PLAN_CONFIG["FREE"])
    new_logos_count = request.batch_size  # ✅ 프론트 요청에 따라 개수 반영

    # 요금제 조건 우회: 관리자 계정은 무제한 허용
    if user.get("is_admin"):
        print("🟢 관리자 계정: 요금제 제한 우회")
        limits = {"max_total": 99999, "max_batch": 100, "max_download": 9999, "s3_retention_days": 365}

    # 선택한 개수가 요금제 허용보다 많으면 차단
    if new_logos_count > limits["max_batch"]:
        raise HTTPException(
            status_code=403,
            detail=f"{plan} 플랜에서는 한 번에 최대 {limits['max_batch']}개까지 생성할 수 있습니다."
        )

    # 총 개수 제한 체크
    current_count = db.query(models.Logo).filter(models.Logo.user_id == request.user_id).count()
    if current_count + new_logos_count > limits["max_total"]:
        raise HTTPException(
            status_code=403,
            detail=f"{plan} 플랜에서는 최대 {limits['max_total']}개의 로고까지만 생성할 수 있습니다."
        )
    
    sanitized_colors = [color.replace("#", "") for color in request.colors]
    if not sanitized_colors:
        sanitized_colors = ["000000"]  # 기본 색상: 검정
        
    color_key = "_".join(color.lstrip("#") for color in request.colors)
    brand_key = request.brand_name.replace(" ", "_")
    folder_name = f"{request.logo_style}_{color_key}_{brand_key}"

    user_folder = os.path.join(BASE_LOGO_FOLDER, request.user_id, folder_name)
    paid_folder = os.path.join(PAID_LOGO_FOLDER, request.user_id, folder_name)
    os.makedirs(user_folder, exist_ok=True)
    os.makedirs(paid_folder, exist_ok=True)

    print("🟢 현재 요금제:", plan)
    print("🟢 현재 생성된 로고 수:", current_count)
    print("🟢 요청된 batch_size:", new_logos_count)
    print("🟢 요금제 허용 최대:", limits)

    generated_logos = []
    for _ in range(new_logos_count):
        logo_id = str(uuid.uuid4())
        logo_filename = f"{logo_id}.png"

        prompt = generate_prompt_with_gpt(
            brand_name=request.brand_name,
            logo_style=request.logo_style,
            font_style=request.font_style or "modern sans-serif",
            colors=request.colors,
            style_detail=request.style_detail,
            core_object=request.core_object,
            background=request.background or "black"
        )
        # ✅ 디버깅용 출력
        print("🧪 최종 프롬프트:", prompt)

        try:
            generated_path = generate_logo_image(prompt)
        except RuntimeError as e:
            print("❌ 로고 생성 중 오류:", str(e))
            raise HTTPException(status_code=500, detail=str(e))

        # ✅ 원본 → paid 폴더로 복사
        paid_logo_path = os.path.join(paid_folder, logo_filename)
        shutil.copy(generated_path, paid_logo_path)

        # ✅ 워터마크 버전 저장
        logo_path = os.path.join(user_folder, logo_filename)
        img = Image.open(generated_path)
        img_watermarked = apply_rotated_watermark(img, text="BRANDIEAI")
        img_watermarked.save(logo_path)

        # ✅ S3 업로드 - 워터마크 버전
        retry_attempts = 3
        s3_url = None
        for attempt in range(retry_attempts):
            s3_url = upload_to_s3(logo_path, f"{request.user_id}/{folder_name}/watermarked/{logo_filename}")
            if s3_url:
                break

        # ✅ S3 업로드 - 워터마크 없는 원본도 저장
        s3_url_original = None
        for attempt in range(retry_attempts):
            s3_url_original = upload_to_s3(paid_logo_path, f"{request.user_id}/{folder_name}/original/{logo_filename}")
            if s3_url_original:
                break

        db_logo = models.Logo(
            user_id=request.user_id,
            logo_path=paid_logo_path,  # 👈 [수정 1] 원본 로컬 경로로 저장
            s3_url=s3_url if s3_url else "", # 워터마크 버전 S3 URL
            s3_url_original=s3_url_original if s3_url_original else "", # 👈 [수정 2] 원본 S3 URL 추가
            brand_name=request.brand_name,
            logo_style=request.logo_style,
            colors=",".join(request.colors)
        )
        db.add(db_logo)
        db.commit()
        db.refresh(db_logo)

        if not s3_url:
            logging.error(f"S3 업로드 실패: {logo_path}")
            raise HTTPException(status_code=500, detail="S3 업로드에 실패했습니다.")
        logo_url = s3_url
        generated_logos.append({
            "logo_id": logo_id,
            "logo_url": logo_url
        })

    return {"user_id": request.user_id, "logos": generated_logos}

@app.get("/logos/{user_id}")
def get_user_logos(
    user_id: str,
    style: Optional[str] = None,
    colors: Optional[str] = None,
    brand_name: Optional[str] = None,
    offset: int = Query(0, alias="offset"),
    limit: int = Query(40, alias="limit"),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # 🔒 권한검사
    if user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    query = db.query(models.Logo).filter(models.Logo.user_id == user_id)

    if style:
        query = query.filter(models.Logo.logo_style == style)
    if colors:
        color_filters = colors.split(",")
        query = query.filter(and_(*(models.Logo.colors.like(f"%{color}%") for color in color_filters)))
    if brand_name:
        query = query.filter(models.Logo.brand_name.like(f"%{brand_name}%"))

    total_count = query.count()
    logos = query.offset(offset).limit(limit).all()

    favorite_logo_ids = set(
        row.logo_id for row in db.query(models.Favorite.logo_id).filter_by(user_id=int(user_id)).all()
    )

    return {
        "user_id": user_id,
        "total_count": total_count,
        "logos": [
            {
                "id": logo.id,
                "user_id": logo.user_id,
                "s3_url": generate_presigned_url_from_s3_url(logo.s3_url) if logo.s3_url else "",
                "brand_name": logo.brand_name,
                "style": logo.logo_style,
                "colors": logo.colors,
                "is_favorite": logo.id in favorite_logo_ids  # ✅ 이 부분 중요
            }
            for logo in logos
        ]
    }

@app.get("/logos/count/{user_id}")
def get_logo_count(
    user_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # 🔒 권한검사
    if user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    count = db.query(models.Logo).filter(models.Logo.user_id == user_id).count()
    return {"user_id": user_id, "logo_count": count}

@app.get("/logos/{user_id}/{folder}/{logo_filename}")
def get_logo(user_id: str, folder: str, logo_filename: str):
    logo_path = os.path.join(BASE_LOGO_FOLDER, user_id, folder, logo_filename)
    if not os.path.exists(logo_path):
        print(f"❌ Logo file not found: {logo_path}")
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(logo_path, media_type="image/png")

@app.get("/logos/paid/{user_id}/{folder}/{logo_filename}")
def get_paid_logo(user_id: str, folder: str, logo_filename: str):
    paid_logo_path = os.path.join(PAID_LOGO_FOLDER, user_id, folder, logo_filename)
    if not os.path.exists(paid_logo_path):
        print(f"❌ Paid logo file not found: {paid_logo_path}")
        raise HTTPException(status_code=404, detail="Logo not found")
    return FileResponse(paid_logo_path, media_type="image/png")

@app.get("/logos/history/{user_id}")
def get_user_logo_history(
    user_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # 🔒 권한검사
    if user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    logos = db.query(models.Logo).filter(models.Logo.user_id == user_id).all()
    if not logos:
        return {"message": "No logo history found for this user."}
    return {
        "user_id": user_id,
        "logos": [
            {
                "id": logo.id,
                "s3_url": generate_presigned_url_from_s3_url(logo.s3_url),
                "brand_name": logo.brand_name,
                "style": logo.logo_style,
                "colors": logo.colors
            }
            for logo in logos
        ]
    }

@app.post("/users/")
def create_user(username: str, email: str, db: Session = Depends(get_db)):
    user = models.User(username=username, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User created successfully", "user": user}

@app.delete("/delete-logo/{logo_id}")
def delete_logo(
    logo_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    logo = db.query(models.Logo).filter(models.Logo.id == logo_id).first()
    if not logo:
        raise HTTPException(status_code=404, detail="Logo not found")
    # 🔒 권한검사
    if logo.user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    if logo.s3_url:
        from backend.s3_utils import delete_from_s3
        delete_from_s3(logo.s3_url)
    if os.path.exists(logo.logo_path):
        os.remove(logo.logo_path)
    db.delete(logo)
    db.commit()
    return {"message": "로고가 성공적으로 삭제되었습니다."}

# ★ 추가: 다중 로고 삭제 API 엔드포인트 (Bulk Delete)
@app.post("/delete-logos")
def delete_logos(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # 🔒 권한검사
    if request.user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    logos_to_delete = db.query(models.Logo).filter(
        models.Logo.user_id == request.user_id,
        models.Logo.id.in_(request.logo_ids)
    ).all()
    if not logos_to_delete:
        raise HTTPException(status_code=404, detail="삭제할 로고가 없습니다.")
    for logo in logos_to_delete:
        if logo.s3_url:
            from backend.s3_utils import delete_from_s3
            delete_from_s3(logo.s3_url)
        if os.path.exists(logo.logo_path):
            os.remove(logo.logo_path)
        db.delete(logo)
    db.commit()
    return {"message": f"{len(logos_to_delete)}개의 로고가 성공적으로 삭제되었습니다."}

@app.get("/user/{user_id}")
def get_user_plan(
    user_with_plan: models.User = Depends(get_user_with_plan) # 의존성 주입!
):
    # 모든 복잡한 로직이 사라지고, 전문가가 준 결과만 사용하면 됩니다.
    plan = (user_with_plan.plan or "FREE").upper()
    limits = PLAN_CONFIG.get(plan, PLAN_CONFIG["FREE"])

    return {
        "id": user_with_plan.id,
        "plan": plan,
        **limits
    }

@app.get("/test-db-connection", tags=["테스트"])
def test_db_connection(db: Session = Depends(get_db)):
    """
    Render 서버에서 Railway DB로의 연결을 직접 테스트하는 임시 API
    """
    try:
        # DB에 아주 간단한 쿼리를 실행하여 연결을 테스트합니다.
        db.execute(text("SELECT 1"))
        return {"status": "success", "message": "✅ 데이터베이스 연결에 성공했습니다!"}
    except Exception as e:
        # 연결 실패 시, 오류 메시지를 자세히 반환합니다.
        # traceback을 포함하여 어떤 종류의 오류인지 명확하게 확인합니다.
        import traceback
        return {
            "status": "error", 
            "message": "❌ 데이터베이스 연결 실패",
            "error_type": str(type(e)),
            "error_details": str(e),
            "traceback": traceback.format_exc()
        }

# --- 라우터 등록 ---
app.include_router(admin.router)
app.include_router(jwt_auth_router)
app.include_router(google_auth_router)
app.include_router(favorites_router)
print("✅ downloads_router 등록 시작")
app.include_router(downloads_router)
app.include_router(download_upscaled_router)

# ✅ 수정된 부분: 결제 라우터를 prefix 없이 등록합니다.
app.include_router(payment_router)

# Google Client ID 전달용 라우터 (별도 파일 대신 여기에 간단히 정의 가능)
@app.get("/auth/google/client-id")
async def get_google_client_id():
    return {"client_id": os.getenv("GOOGLE_CLIENT_ID")}

# # --- 예약 작업 ---
# @app.on_event("startup")
# @repeat_every(seconds=86400) # 24시간마다 자동 실행
# def schedule_s3_cleanup():
#     clean_expired_s3_logos()

# --- 메인 실행 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)