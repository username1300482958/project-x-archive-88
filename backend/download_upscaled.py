from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.auth_jwt_utils import get_current_user
from backend.database import get_db
from backend.models import User, Logo
from backend.upscale_utils import upscale_image_with_replicate
import os

router = APIRouter()

@router.get("/download/highres/{user_id}/{logo_id}")
def download_highres_logo(
    user_id: str,
    logo_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # ✅ 권한 확인
    if user["sub"] != user_id:
        raise HTTPException(status_code=403, detail="권한이 없습니다.")

    # ✅ 유저 및 요금제 확인
    user_obj = db.query(User).filter(User.id == user_id).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    allowed_plans = {"PRO", "ENTERPRISE"}
    plan = (user_obj.plan or "FREE").upper()
    if plan not in allowed_plans:
        raise HTTPException(status_code=403, detail=f"{plan} 요금제에서는 고화질 다운로드가 제공되지 않습니다.")

    # ✅ 로고 조회
    logo = db.query(Logo).filter(Logo.id == logo_id, Logo.user_id == user_id).first()
    if not logo:
        raise HTTPException(status_code=404, detail="로고를 찾을 수 없습니다.")

    # ✅ 원본 로고 경로 확인
    original_path = logo.logo_path
    if not original_path or not os.path.exists(original_path):
        raise HTTPException(status_code=404, detail="로고 원본 파일이 존재하지 않습니다.")

    # ✅ 업스케일링 수행 + S3 업로드 + Presigned URL 생성
    try:
        presigned_url = upscale_image_with_replicate(original_path, scale=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"업스케일링 실패: {str(e)}")

    # ✅ 최종 응답: presigned URL 리턴
    return { "highres_url": presigned_url }