import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Logo, User
from .s3_utils import delete_from_s3
from sqlalchemy import join # 👈 [추가] JOIN을 위해 import

# 환경 변수 로드
load_dotenv()

# 👇 [수정 1] 가격 정책과 플랜 이름을 정확히 일치시킵니다.
PLAN_RETENTION_DAYS = {
    "FREE": 7,
    "BASIC": 90,         # 'STARTER' -> 'BASIC'
    "PRO": 180,
    "ENTERPRISE": 365,
}

def clean_expired_s3_logos():
    print("🧹 S3 보관기한 초과 로고 정리 시작")
    db: Session = SessionLocal()

    try:
        now = datetime.utcnow()
        expired_logo_ids = []

        # 👇 [수정 2 & 3] 모든 로고를 불러오는 대신, JOIN을 사용해 단 한 번의 효율적인 쿼리로 변경합니다.
        # Logo와 User 테이블을 합쳐서(join), 각 로고와 그 주인의 plan 정보를 한 번에 가져옵니다.
        query = db.query(Logo, User.plan).select_from(Logo).join(User, User.id == Logo.user_id)
        
        # 반복문은 이제 훨씬 더 적은 데이터로, DB 조회 없이 실행됩니다.
        for logo, user_plan in query.all():
            if not hasattr(logo, "created_at") or not logo.created_at:
                continue

            plan = (user_plan or "FREE").upper()
            # 기본값을 7일(FREE 플랜)로 설정하여 안정성 확보
            retention_days = PLAN_RETENTION_DAYS.get(plan, 7)
            expiration_date = logo.created_at + timedelta(days=retention_days)

            if now > expiration_date:
                print(f"⏰ 삭제 대상 로고: ID={logo.id}, 생성일={logo.created_at}, 요금제={plan}")
                
                # 원본과 워터마크 S3 URL 모두 삭제 시도
                if logo.s3_url:
                    delete_from_s3(logo.s3_url)
                if hasattr(logo, 's3_url_original') and logo.s3_url_original:
                    delete_from_s3(logo.s3_url_original)
                    
                expired_logo_ids.append(logo.id)

        if expired_logo_ids:
            # 한 번에 모든 만료된 로고를 DB에서 삭제
            db.query(Logo).filter(Logo.id.in_(expired_logo_ids)).delete(synchronize_session=False)
            db.commit()
            print(f"✅ 총 {len(expired_logo_ids)}개 로고 삭제 완료")
        else:
            print("✅ 삭제할 만료 로고 없음")

    except Exception as e:
        print(f"❌ S3 정리 중 예외 발생: {str(e)}")
        db.rollback() # 예외 발생 시 롤백 추가

    finally:
        db.close()
        print("🧹 S3 정리 작업 종료")

if __name__ == "__main__":
    clean_expired_s3_logos()