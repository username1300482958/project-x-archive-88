from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .auth_jwt_utils import get_current_user, get_user_with_plan
from .database import get_db
from .models import User, Logo
from .upscale_utils import upscale_image_with_replicate
from .tasks import process_high_res_image
from .s3_utils import generate_presigned_url_from_s3_url, s3_client, AWS_S3_BUCKET_NAME
from urllib.parse import urlparse
import os
import boto3
import io

router = APIRouter()

# 🔽 엔드포인트 이름과 방식을 더 명확하게 변경합니다. (GET -> POST)
#    '다운로드'가 아닌 '생성 요청'이므로 POST가 더 적합합니다.
@router.post("/request-high-res/{logo_id}", status_code=status.HTTP_202_ACCEPTED)
def request_high_res_logo(
    logo_id: int, # user_id는 JWT 토큰에서 얻으므로 URL에서 제거
    db: Session = Depends(get_db),
    user_obj: User = Depends(get_user_with_plan)
):
    # --- 권한 및 요금제 확인 로직 (기존과 동일) ---
    allowed_plans = {"PRO", "ENTERPRISE"}
    plan = (user_obj.plan or "FREE").upper()
    if plan not in allowed_plans:
        raise HTTPException(status_code=403, detail=f"{plan} 요금제에서는 고화질 다운로드가 제공되지 않습니다.")

    # --- 로고 소유권 확인 및 원본 URL 가져오기 (user_obj.id 사용) ---
    logo = db.query(Logo).filter(Logo.id == logo_id, Logo.user_id == user_obj.id).first()
    
    if not logo or not logo.s3_url_original:
        raise HTTPException(status_code=404, detail="업스케일링할 원본 로고의 S3 URL이 없습니다.")
    
    # --- 🔽 여기가 핵심 변경 부분입니다 🔽 ---
    # 기존의 S3 다운로드, Replicate 호출 등 모든 무거운 로직을 삭제합니다.
    
    # Celery에게 "이 일 좀 해줘!" 라고 작업을 지시하고 바로 넘어갑니다.
    # Replicate URL 대신 원본 S3 URL을 넘겨주고, 작업 내부에서 Replicate를 호출하도록 합니다.
    # (이 부분은 tasks.py를 어떻게 구현했느냐에 따라 달라질 수 있습니다.)
    # 지금은 Replicate URL이 이미 DB에 저장되어 있다는 가정하에 진행하겠습니다.
    
    if not logo.replicate_url: # DB에 Replicate URL이 있는지 확인
         raise HTTPException(status_code=400, detail="Upscaled URL from Replicate is not available yet.")

    # Celery 작업 큐에 작업을 넣습니다. .delay()를 호출하면 끝!
    process_high_res_image.delay(replicate_url=logo.replicate_url, logo_id=logo.id)
    
    # 사용자에게는 즉시 "요청 접수" 응답을 보냅니다.
    return {"status": "processing", "message": "High-resolution image generation has started. It will be available for download in a minute."}