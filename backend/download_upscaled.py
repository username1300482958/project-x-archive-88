from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth_jwt_utils import get_current_user, get_user_with_plan
from .database import get_db
from .models import User, Logo
from .upscale_utils import upscale_image_with_replicate
from .s3_utils import generate_presigned_url_from_s3_url, s3_client, AWS_S3_BUCKET_NAME
from urllib.parse import urlparse
import os
import boto3
import io

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
    
    # DB에 저장된 's3_url_original'을 확인합니다.
    if not logo or not logo.s3_url_original:
        raise HTTPException(status_code=404, detail="업스케일링할 원본 로고의 S3 URL이 없습니다.")

    original_s3_url = logo.s3_url_original

    try:
        # S3 URL을 안전하게 파싱하여 객체 키를 추출합니다.
        parsed_url = urlparse(original_s3_url)
        # URL 경로의 맨 앞 '/'를 제거하여 순수한 객체 키만 남깁니다.
        object_key = parsed_url.path.lstrip('/')
        
        print(f"S3에서 다운로드할 객체 키: {object_key}") # 디버깅용 로그 추가

        in_mem_file = io.BytesIO()
        s3_client.download_fileobj(AWS_S3_BUCKET_NAME, object_key, in_mem_file)
        in_mem_file.seek(0)

        # upscale_utils의 함수를 호출하여 업스케일링을 진행합니다.
        presigned_url = upscale_image_with_replicate(in_mem_file, scale=2)

    except Exception as e:
        error_detail = str(e)
        print(f"❌ 업스케일링 실패: {error_detail}")
        raise HTTPException(status_code=500, detail=f"업스케일링 실패: {error_detail}")

    return {"highres_url": presigned_url}