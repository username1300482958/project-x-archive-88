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

# 수정 후 코드
@router.get("/download/{user_id}/{logo_id}") # '/original' 삭제
def download_logo(  # 함수 이름 변경
    user_id: str,
    logo_id: int,
    db: Session = Depends(get_db),
    user_obj: User = Depends(get_user_with_plan)
):  
    # DB를 또 조회할 필요 없이, 전문가가 준 결과(user_obj)를 바로 사용합니다.
    plan = (user_obj.plan or "FREE").upper()
    if plan == "FREE":
        raise HTTPException(status_code=403, detail="FREE 요금제에서는 다운로드할 수 없습니다.")

    logo = db.query(Logo).filter(Logo.id == logo_id, Logo.user_id == user_id).first()
    # 👇 s3_url_original 대신 일반 s3_url을 사용해야 할 수 있습니다. 로고 모델 정의에 따라 맞춰주세요.
    if not logo or not getattr(logo, "s3_url", None): 
        raise HTTPException(status_code=404, detail="로고 URL이 없습니다.")

    from backend.s3_utils import generate_presigned_url_from_s3_url
    
    # 👇 반환하는 URL 키 이름과 사용하는 로고 URL 속성을 프론트와 일치시킵니다.
    presigned_url = generate_presigned_url_from_s3_url(logo.s3_url) 
    return {"logo_url": presigned_url} # 'original_url' -> 'logo_url'