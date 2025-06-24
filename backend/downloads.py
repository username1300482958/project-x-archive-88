from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .auth_jwt_utils import verify_token, get_user_id_from_token
from .database import get_db
from .models import User, Download, Logo
from .auth_jwt_utils import get_current_user, get_user_with_plan

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
router = APIRouter()

# 🔽 이걸 추가해야 출력이 콘솔에 확실히 찍힘
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

@router.get("/download/count/{user_id}")
def get_download_count(
    user_id: str,
    user: dict = Depends(get_current_user),  # ✅ 헤더 기반 토큰
    db: Session = Depends(get_db)
):
    logger.debug("✅ 진입")
    logger.debug(f"🔑 JWT sub: {user.get('sub')}")
    logger.debug(f"🔗 URL param: {user_id}")
    logger.debug(f"⚖ 비교 결과: {user.get('sub') == user_id}")
    logger.debug(f"📏 타입: sub={type(user.get('sub'))}, user_id={type(user_id)}")
    
    # ✅ 관리자 우선 예외 처리
    if not user.get("is_admin"):
        # 일반 사용자는 user_id가 본인 것과 일치해야 함
        if str(user["sub"]).strip() != str(user_id).strip():
            raise HTTPException(status_code=403, detail="권한이 없습니다.")
    else:
        logger.debug("🟢 관리자 계정: user_id 권한 검사 우회")

    # ✅ 유저 존재 여부 확인
    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    plan_limit_map = {
        "FREE": 0,
        "STARTER": 3,
        "BASIC": 3,         # ✅ BASIC 명시적 추가
        "PRO": 10,
        "ENTERPRISE": 20    # ✅ ENTERPRISE 요금제 추가
    }
    plan = getattr(user_obj, "plan", "FREE") or "FREE"
    allowed = plan_limit_map.get(plan.upper(), 0)

    # ✅ 이미 다운로드한 횟수 계산
    used = db.query(Download).filter(
        Download.user_id == user_id
    ).count()

    return {"used": used, "allowed": allowed, "plan": plan.upper()}

@router.get("/download/{user_id}/{logo_id}")
def download_logo(
    user_id: str,
    logo_id: int,
    db: Session = Depends(get_db),
    user_obj: User = Depends(get_user_with_plan)
):
    plan = (user_obj.plan or "FREE").upper()

    # 👇 다운로드 횟수 제한을 확인하는 로직 추가
    plan_limit_map = {
        "FREE": 0, "STARTER": 3, "BASIC": 3, "PRO": 10, "ENTERPRISE": 20
    }
    allowed = plan_limit_map.get(plan, 0)
    used = db.query(Download).filter(Download.user_id == user_id).count()

    if used >= allowed:
        raise HTTPException(
            status_code=403,
            detail=f"{plan} 플랜에서는 최대 {allowed}개의 로고만 다운로드할 수 있습니다."
        )
    # 👆 여기까지가 추가된 부분

    logo = db.query(Logo).filter(Logo.id == logo_id, Logo.user_id == user_id).first()
    if not logo or not getattr(logo, "s3_url", None):
        raise HTTPException(status_code=404, detail="로고 URL이 없습니다.")
    
    # 👇 원본 URL(s3_url_original)을 우선적으로 사용하도록 변경합니다.
    download_target_url = logo.s3_url_original if logo.s3_url_original else logo.s3_url
    if not download_target_url:
        raise HTTPException(status_code=404, detail="로고 URL이 없습니다.")

    # 다운로드 기록 저장
    new_download = Download(user_id=user_id, logo_id=logo_id)
    db.add(new_download)
    db.commit()

    from backend.s3_utils import generate_presigned_url_from_s3_url
    # 👇 s3_utils에 만든 download_name 파라미터를 사용하여 파일명을 지정해줍니다.
    presigned_url = generate_presigned_url_from_s3_url(
        download_target_url, 
        download_name=f"{logo.brand_name}_logo.png"
    )
    return {"logo_url": presigned_url}