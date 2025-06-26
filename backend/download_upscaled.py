# download_upscaled.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import traceback

# --- 로컬 모듈 ---
from .database import get_db
from .models import User, Logo, Download
from .auth_jwt_utils import get_user_with_plan
from .upscale_utils import upscale_image_with_replicate
from .s3_utils import generate_presigned_url_from_s3_url

router = APIRouter(
    prefix="/download/highres",
    tags=["Download High-Resolution"]
)

@router.get("/{user_id}/{logo_id}")
def download_highres_logo(
    user_id: str,
    logo_id: int,
    db: Session = Depends(get_db),
    user_obj: User = Depends(get_user_with_plan)
):
    """
    [프로덕션 최종본]
    사용자의 플랜과 '전체' 다운로드 횟수를 확인한 뒤, 업스케일링을 수행하고
    다운로드 URL을 반환하며, 성공 시 다운로드 기록을 DB에 남깁니다.
    """
    # 1. 요금제 확인 (PRO 플랜 이상만 허용)
    plan = (user_obj.plan or "FREE").upper()
    if plan not in {"PRO", "ENTERPRISE"}:
        raise HTTPException(status_code=403, detail=f"{plan} 요금제에서는 고화질 다운로드가 제공되지 않습니다.")

    # 2. 다운로드 횟수 제한 확인 (기존 downloads.py 로직과 동일하게)
    #    고화질/일반 구분 없이 '전체' 다운로드 횟수를 기준으로 계산합니다.
    highres_plan_limit_map = {
        "PRO": 10,
        "ENTERPRISE": 99999 
    }
    max_downloads = highres_plan_limit_map.get(plan, 0)
    
    # ▼▼▼▼ [수정 1] 'Download.type' 필터링 제거 ▼▼▼▼
    current_downloads = db.query(Download).filter(
        Download.user_id == user_id
    ).count()

    if current_downloads >= max_downloads:
        raise HTTPException(
            status_code=403,
            detail=f"{plan} 요금제의 다운로드 한도({max_downloads}회)를 모두 사용하셨습니다. (고화질 포함)"
        )

    # 3. DB에서 로고 정보 조회
    logo = db.query(Logo).filter(Logo.id == logo_id, Logo.user_id == user_id).first()
    if not logo or not logo.s3_url_original:
        raise HTTPException(status_code=404, detail="업스케일링할 원본 로고를 찾을 수 없습니다.")

    # 4. 업스케일링 및 URL 생성 (성공이 검증된 로직)
    try:
        presigned_original_url = generate_presigned_url_from_s3_url(
            logo.s3_url_original,
            expiration=300
        )
        if not presigned_original_url:
            raise RuntimeError("원본 이미지의 임시 접근 주소 생성에 실패했습니다.")
        
        final_download_url = upscale_image_with_replicate(presigned_original_url, scale=2)

    except Exception as e:
        error_detail = str(e)
        print(f"❌ 업스케일링 실패: {error_detail}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"업스케일링 실패: {error_detail}")

    # 5. 성공 시 다운로드 기록 DB에 저장
    try:
        # ▼▼▼▼ [수정 2] 'type' 필드 제거 ▼▼▼▼
        new_download = Download(
            user_id=user_id,
            logo_id=logo_id,
            downloaded_at=datetime.utcnow()
        )
        db.add(new_download)
        db.commit()
        print(f"✅ DB에 다운로드 기록 저장 완료 (User: {user_id}, Logo: {logo_id})")
    except Exception as e:
        db.rollback()
        print(f"🔥🔥🔥 심각한 오류: 다운로드 기록 DB 저장 실패! User: {user_id}, Logo: {logo_id}, Error: {e}")
        traceback.print_exc()

    # 6. 최종 URL 반환
    return {"highres_url": final_download_url}