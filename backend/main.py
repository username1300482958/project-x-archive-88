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
from .prompt_designer import create_design_brief_from_gpt
from .utils_watermark import apply_watermark_to_svg
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
    print("✅ NEW PIPELINE: /generate-logo 진입")
    
    # --- 1. 사용자 인증, 권한 및 요금제 확인 (기존 로직 그대로 유지) ---
    client_ip = get_client_ip(req)
    print(f"📡 요청자 IP: {client_ip}")

    if request.user_id != user["sub"]:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")
    
    # Abuse 방지 필터링
    three_hours_ago = datetime.utcnow() - timedelta(hours=3)
    recent_free_user_ids = (
        db.query(models.User.id)
        .join(models.Logo, models.User.id == models.Logo.user_id)
        .filter(
            models.User.plan == "FREE",
            models.Logo.created_at >= three_hours_ago,
            models.Logo.user_id != request.user_id
        )
        .distinct().all()
    )
    recent_user_ids = [row.id for row in recent_free_user_ids]

    if recent_user_ids:
        recent_ips = (
            db.query(models.ErrorLog.user_id, models.ErrorLog.message)
            .filter(
                models.ErrorLog.user_id.in_(recent_user_ids),
                models.ErrorLog.context == "AbuseCheck"
            ).all()
        )
        for uid, logged_ip in recent_ips:
            if logged_ip == client_ip:
                print(f"🚫 abuse 감지됨: IP={client_ip}, 다른 FREE 유저={uid}")
                raise HTTPException(status_code=429, detail="FREE 요금제는 동일 IP에서 일정 시간 내 중복 생성이 제한됩니다.")

    log_error(user_id=request.user_id, context="AbuseCheck", message=client_ip)

    # 플랜 결정 로직
    plan = "FREE"
    YOUR_DEVELOPER_USER_ID = "104120949912979219868"
    if user.get("is_admin") or request.user_id == YOUR_DEVELOPER_USER_ID:
        plan = "ENTERPRISE"
        print(f"🟢 관리자/개발자 계정으로 확인됨. 플랜을 {plan}로 설정합니다.")
    else:
        user_obj = db.query(models.User).filter(models.User.id == request.user_id).first()
        if user_obj and user_obj.plan:
            plan = user_obj.plan.upper()
    
    # 요금제 한도 확인
    limits = PLAN_CONFIG.get(plan, PLAN_CONFIG["FREE"])
    new_logos_count = request.batch_size
    if new_logos_count > limits["max_batch"]:
        raise HTTPException(status_code=403, detail=f"{plan} 플랜에서는 한 번에 최대 {limits['max_batch']}개까지 생성할 수 있습니다.")
    
    current_count = db.query(models.Logo).filter(models.Logo.user_id == request.user_id).count()
    if current_count + new_logos_count > limits["max_total"]:
        raise HTTPException(status_code=403, detail=f"{plan} 플랜에서는 최대 {limits['max_total']}개의 로고까지만 생성할 수 있습니다.")
    
    print(f"🟢 Plan: {plan}, Batch Size: {request.batch_size}")
    
    # --- 2. 새로운 로고 생성 파이프라인 실행 (핵심 로직 교체) ---
    generated_logos = []
    for i in range(request.batch_size):
        print(f"--- 로고 생성 시작 [{i+1}/{request.batch_size}] ---")

        # 2-1. GPT-4o를 호출하여 사용자의 모든 선택이 반영된 '디자인 브리프'를 생성합니다.
        design_brief = create_design_brief_from_gpt(
            brand_name=request.brand_name,
            logo_style=request.logo_style,
            colors=request.colors,
            font_style=request.font_style,
            core_object=request.core_object
        )
        
        if "error" in design_brief:
            print(f"❌ 디자인 브리프 생성 실패: {design_brief['error']}")
            continue

        # 2-2. SVG '리모델링': 플레이스홀더를 실제 값으로 교체합니다.
        svg_template = design_brief.get("svg_template", "")
        
        # 폰트 결정: 사용자가 선택한 폰트 > AI가 제안한 폰트 > 기본 폰트 순으로 적용
        font_map = {
            "modern": '"Noto Sans KR", sans-serif',
            "classic": '"Nanum Myeongjo", serif',
            "rounded": '"Cafe24Ssurround", cursive',
            "handwritten": '"Dongle", cursive'
        }
        final_font_family = font_map.get(request.font_style, design_brief.get("font_suggestion", "Arial, sans-serif"))

        # 색상 결정: 사용자가 선택한 색상 > AI가 제안한 색상 > 기본 색상 순으로 적용
        palette = design_brief.get("color_palette", {})
        final_colors = request.colors if request.colors else list(palette.values())
        
        svg_content = svg_template.replace("{{BRAND_NAME}}", request.brand_name)
        svg_content = svg_content.replace("{{COLOR_PRIMARY}}", final_colors[0] if len(final_colors) > 0 else "#000000")
        svg_content = svg_content.replace("{{COLOR_SECONDARY}}", final_colors[1] if len(final_colors) > 1 else (final_colors[0] if len(final_colors) > 0 else "#CCCCCC"))
        svg_content = svg_content.replace("{{COLOR_TEXT}}", final_colors[0] if len(final_colors) > 0 else "#000000")
        
        # 2-3. 최종 SVG 파일 저장 및 S3 업로드
        logo_uuid = uuid.uuid4()
        logo_filename_svg = f"{logo_uuid}.svg"
        
        color_key = "_".join(color.lstrip("#") for color in request.colors)
        brand_key = request.brand_name.replace(" ", "_")
        folder_name = f"{request.logo_style}_{color_key}_{brand_key}"
        
        paid_folder = os.path.join(PAID_LOGO_FOLDER, request.user_id, folder_name)
        os.makedirs(paid_folder, exist_ok=True)
        paid_logo_path = os.path.join(paid_folder, logo_filename_svg)
        with open(paid_logo_path, "w", encoding="utf-8") as f:
            f.write(svg_content)
            
        user_folder = os.path.join(BASE_LOGO_FOLDER, request.user_id, folder_name)
        os.makedirs(user_folder, exist_ok=True)
        watermarked_logo_path = os.path.join(user_folder, logo_filename_svg)
        # --- 👇 이 부분이 교체됩니다 ---
        # 1. 원본 SVG 파일 내용을 읽어옵니다.
        with open(paid_logo_path, "r", encoding="utf-8") as f:
            original_svg_content = f.read()
        
        # 2. 새로운 SVG 워터마크 함수를 호출합니다.
        watermarked_svg_content = apply_watermark_to_svg(original_svg_content)

        # 3. 워터마크가 적용된 내용을 새로운 파일에 씁니다.
        with open(watermarked_logo_path, "w", encoding="utf-8") as f:
            f.write(watermarked_svg_content)
        # --- 👆 여기까지 ---
        
        print("📤 S3 업로드 시도...")
        s3_url_original = upload_to_s3(paid_logo_path, f"{request.user_id}/{folder_name}/original/{logo_filename_svg}")
        s3_url_watermarked = upload_to_s3(watermarked_logo_path, f"{request.user_id}/{folder_name}/watermarked/{logo_filename_svg}")
        
        if not s3_url_original or not s3_url_watermarked:
            raise HTTPException(status_code=500, detail="클라우드 업로드 실패")
        
        print("✅ S3 업로드 성공. DB 저장 시작...")
        db_logo = models.Logo(
            user_id=request.user_id,
            logo_path=paid_logo_path,
            s3_url=s3_url_watermarked,
            s3_url_original=s3_url_original,
            brand_name=request.brand_name,
            logo_style=request.logo_style,
            colors=",".join(request.colors)
        )
        db.add(db_logo)
        db.commit()
        db.refresh(db_logo)
        print(f"✅ 데이터베이스 저장 완료 (Logo ID: {db_logo.id})")

        generated_logos.append({
            "logo_id": db_logo.id,
            "logo_url": s3_url_watermarked
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

@app.get("/generation/count/{user_id}", tags=["Counts"])
def get_generation_count(
    user_id: str,
    db: Session = Depends(get_db),
    user_obj: models.User = Depends(get_user_with_plan)
):
    """
    사용자의 현재 로고 생성 횟수와 플랜별 최대 생성 가능 횟수를 반환합니다.
    """
    plan = (user_obj.plan or "FREE").upper()
    
    # PLAN_CONFIG에서 해당 플랜의 최대 생성 한도를 가져옵니다.
    # .get("max_total", 0)을 사용하여 안전하게 값을 가져옵니다.
    allowed = PLAN_CONFIG.get(plan, PLAN_CONFIG["FREE"]).get("max_total", 0)

    # 현재까지 생성한 로고의 총 개수를 계산합니다.
    used = db.query(models.Logo).filter(models.Logo.user_id == user_id).count()

    return {"used": used, "allowed": allowed, "plan": plan}

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
            "message": "❌ 데이터베이스 연결 실패",#재배포용 주석
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

# --- 메인 실행 ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)