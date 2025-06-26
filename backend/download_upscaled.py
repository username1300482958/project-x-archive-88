# download_upscaled.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .auth_jwt_utils import get_user_with_plan
from .database import get_db
from .models import User, Logo
from .upscale_utils import upscale_image_with_replicate
# s3_utils에서 generate_presigned_url_from_s3_url 함수를 가져옵니다.
from .s3_utils import generate_presigned_url_from_s3_url 
# 아래는 이제 필요 없습니다.
# from .s3_utils import s3_client, AWS_S3_BUCKET_NAME
# from urllib.parse import urlparse
# import io

router = APIRouter()

@router.get("/download/highres/{user_id}/{logo_id}")
def download_highres_logo(
    user_id: str,
    logo_id: int,
    db: Session = Depends(get_db),
    user_obj: User = Depends(get_user_with_plan)
):
    # 요금제 확인 로직 (기존과 동일)
    allowed_plans = {"PRO", "ENTERPRISE"}
    plan = (user_obj.plan or "FREE").upper()
    if plan not in allowed_plans:
        raise HTTPException(status_code=403, detail=f"{plan} 요금제에서는 고화질 다운로드가 제공되지 않습니다.")

    logo = db.query(Logo).filter(Logo.id == logo_id, Logo.user_id == user_id).first()
    
    if not logo or not logo.s3_url_original:
        raise HTTPException(status_code=404, detail="업스케일링할 원본 로고의 S3 URL이 없습니다.")

    # --- ▼▼▼▼ 이 부분이 핵심 수정 사항입니다 ▼▼▼▼ ---
    try:
        # 1. S3에서 파일을 직접 다운로드하는 대신, 원본 이미지의 presigned URL을 생성합니다.
        #    이 URL은 일정 시간 동안만 공개적으로 접근 가능합니다.
        presigned_original_url = generate_presigned_url_from_s3_url(
            logo.s3_url_original,
            expires_in=300 # 5분 동안 유효한 링크
        )
        if not presigned_original_url:
            raise RuntimeError("원본 이미지의 임시 접근 주소 생성에 실패했습니다.")

        print(f"Replicate에 전달할 원본 이미지 임시 URL: {presigned_original_url}")

        # 2. upscale_utils의 함수에 파일 객체 대신 'URL 문자열'을 전달하여 업스케일링을 요청합니다.
        #    Replicate 라이브러리는 파일 객체뿐만 아니라 이미지 URL도 input으로 받을 수 있습니다.
        final_download_url = upscale_image_with_replicate(presigned_original_url, scale=2)

    # --- ▲▲▲▲ 여기까지가 핵심 수정 사항입니다 ▲▲▲▲ ---

    except Exception as e:
        # 에러 로깅은 그대로 유지
        import traceback
        error_detail = str(e)
        print(f"❌ 업스케일링 실패: {error_detail}")
        traceback.print_exc() # 더 자세한 에러 추적을 위해 traceback 추가
        raise HTTPException(status_code=500, detail=f"업스케일링 실패: {error_detail}")

    return {"highres_url": final_download_url}