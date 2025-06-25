from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth_jwt_utils import get_current_user, get_user_with_plan
from .database import get_db
from .models import User, Logo
from .upscale_utils import upscale_image_with_replicate
from .s3_utils import generate_presigned_url_from_s3_url
import os

router = APIRouter()

@router.get("/download/highres/{user_id}/{logo_id}")
def download_highres_logo(
    user_id: str,
    logo_id: int,
    db: Session = Depends(get_db),
    user_obj: User = Depends(get_user_with_plan)
):
    allowed_plans = {"PRO", "ENTERPRISE"}
    plan = (user_obj.plan or "FREE").upper()
    if plan not in allowed_plans:
        raise HTTPException(status_code=403, detail=f"{plan} 요금제에서는 고화질 다운로드가 제공되지 않습니다.")

    logo = db.query(Logo).filter(Logo.id == logo_id, Logo.user_id == user_id).first()
    
    # 👇 이제 로컬 경로 대신, DB에 저장된 's3_url_original'을 확인합니다.
    if not logo or not logo.s3_url_original:
        raise HTTPException(status_code=404, detail="업스케일링할 원본 로고의 S3 URL이 없습니다.")

    # 👇 로컬 파일을 찾는 모든 로직을 삭제합니다.
    original_s3_url = logo.s3_url_original

    # 👇 [추가] Replicate가 접근할 수 있도록, 원본 S3 URL에 대한 임시 공개 주소(Presigned URL)를 먼저 생성합니다.
    # 이 임시 주소는 짧은 시간(예: 5분)만 유효합니다.
    accessible_url = generate_presigned_url_from_s3_url(original_s3_url, expiration=300)
    
    try:
        # 👇 이제 Replicate에게는 이 임시 공개 주소를 전달합니다.
        presigned_url = upscale_image_with_replicate(accessible_url, scale=2)
    except Exception as e:
        error_detail = str(e)
        print(f"❌ 업스케일링 실패: {error_detail}")
        raise HTTPException(status_code=500, detail=f"업스케일링 실패: {error_detail}")

    return { "highres_url": presigned_url }