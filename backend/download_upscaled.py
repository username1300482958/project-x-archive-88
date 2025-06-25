from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth_jwt_utils import get_current_user, get_user_with_plan
from .database import get_db
from .models import User, Logo
from .upscale_utils import upscale_image_with_replicate
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
    
    try:
        # 👇 이제 s3_url_original을 직접 전달하여 업스케일링을 수행합니다.
        presigned_url = upscale_image_with_replicate(original_s3_url, scale=2)
    except Exception as e:
        # Replicate에서 오는 에러를 좀 더 구체적으로 보여주도록 수정
        error_detail = str(e)
        print(f"❌ 업스케일링 실패: {error_detail}")
        raise HTTPException(status_code=500, detail=f"업스케일링 실패: {error_detail}")

    return { "highres_url": presigned_url }