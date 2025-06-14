import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from backend.database import SessionLocal
from backend.models import Logo, User
from backend.s3_utils import delete_from_s3

# 환경 변수 로드
load_dotenv()

# 요금제별 보관 기간 (일)
PLAN_RETENTION_DAYS = {
    "FREE": 7,
    "STARTER": 90,       # BASIC 플랜
    "PRO": 180,          # PRO 플랜
    "ENTERPRISE": 365,   # ENTERPRISE 플랜
}

def clean_expired_s3_logos():
    print("🧹 S3 보관기한 초과 로고 정리 시작")
    db: Session = SessionLocal()

    try:
        now = datetime.utcnow()
        logos = db.query(Logo).all()
        expired_logo_ids = []

        for logo in logos:
            user = db.query(User).filter(User.id == logo.user_id).first()
            if not user or not hasattr(logo, "created_at"):
                continue

            plan = (user.plan or "FREE").upper()
            retention_days = PLAN_RETENTION_DAYS.get(plan, 3)
            expiration_date = logo.created_at + timedelta(days=retention_days)

            if now > expiration_date:
                print(f"⏰ 삭제 대상 로고: ID={logo.id}, 생성일={logo.created_at}, 요금제={plan}")
                if logo.s3_url:
                    delete_from_s3(logo.s3_url)
                expired_logo_ids.append(logo.id)

        if expired_logo_ids:
            db.query(Logo).filter(Logo.id.in_(expired_logo_ids)).delete(synchronize_session=False)
            db.commit()
            print(f"✅ 총 {len(expired_logo_ids)}개 로고 삭제 완료")
        else:
            print("✅ 삭제할 만료 로고 없음")

    except Exception as e:
        print("❌ S3 정리 중 예외 발생:", str(e))

    finally:
        db.close()
        print("🧹 S3 정리 작업 종료")