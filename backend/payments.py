# payments.py (최종 수정본)

import base64
import os
import uuid
from datetime import datetime
from typing import Optional, List # [추가] List 임포트

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text # ✅ 수정됨: text 함수 import 추가
from starlette.responses import RedirectResponse

from backend.auth_jwt_utils import get_current_user
from backend.database import SessionLocal, get_db # [추가] get_db 임포트
from backend.models import User, Order # [추가] Order 모델 임포트

# --- 초기 설정 ---
load_dotenv()
router = APIRouter()

TOSS_SECRET_KEY = os.getenv("TOSS_SECRET_KEY")
if not TOSS_SECRET_KEY:
    raise RuntimeError("❌ TOSS_SECRET_KEY is not set in environment variables")

FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "https://brandieai.com")


# --- Pydantic 모델 ---
class PaymentConfirmRequest(BaseModel):
    paymentKey: str
    orderId: str
    amount: int

class OrderInfoRequest(BaseModel):
    plan_id: str

# [추가] 결제 내역 조회를 위한 응답 모델
class PaymentHistoryItem(BaseModel):
    orderId: str
    amount: int
    status: str
    requestedAt: datetime
    itemName: str

    class Config:
        orm_mode = True

class PaymentHistoryResponse(BaseModel):
    total_count: int
    payments: List[PaymentHistoryItem]


# --- 핵심 로직: API 엔드포인트 ---

@router.post("/api/v1/payments/confirm", summary="토스페이먼츠 결제 승인")
async def confirm_payment(
    request_data: PaymentConfirmRequest,
    # ✅ 1. JWT 토큰으로 현재 사용자를 확인하는 의존성 추가
    current_user: dict = Depends(get_current_user), 
    db: Session = Depends(lambda: SessionLocal())
):
    encoded_secret_key = base64.b64encode(f"{TOSS_SECRET_KEY}:".encode("utf-8")).decode("utf-8")
    headers = {
        "Authorization": f"Basic {encoded_secret_key}",
        "Content-Type": "application/json",
        "Idempotency-Key": request_data.orderId,
    }
    # 클라이언트가 보낸 payload가 아닌, 서버에서 검증 후 생성할 payload
    # payload = { ... } # 이 부분은 아래에서 다시 정의

    try:
        # --- DB에서 원본 주문 정보 조회 ---
        # ✅ text()로 감싸진 부분은 그대로 유지
        order_in_db_row = db.execute(
            text("SELECT * FROM orders WHERE order_id = :order_id"), 
            {"order_id": request_data.orderId}
        ).first()

        if not order_in_db_row:
            raise HTTPException(status_code=404, detail="주문 정보를 찾을 수 없습니다.")
        
        order_in_db = dict(order_in_db_row._mapping)

        # --- ✅ 2. 보안 검증 로직 추가 (매우 중요) ---

        # 2-1. 주문자와 승인 요청자가 동일한지 확인
        if order_in_db.get("user_id") != current_user["sub"]:
            raise HTTPException(status_code=403, detail="결제를 승인할 권한이 없습니다.")

        # 2-2. DB에 저장된 실제 결제 금액 확인
        stored_amount = get_amount_by_plan(order_in_db.get("plan_id"))

        # 2-3. 클라이언트가 보낸 금액과 DB에 저장된 금액이 일치하는지 확인
        if stored_amount != request_data.amount:
            # 금액이 위변조된 경우. 실제로는 에러 로깅만 하고 사용자에게는 일반적인 실패 메시지를 보여주는 것이 좋습니다.
            print(f"❌ [결제 금액 위변조 시도] DB 금액: {stored_amount}, 요청 금액: {request_data.amount}")
            raise HTTPException(status_code=400, detail="결제 금액이 올바르지 않습니다.")
        
        # --- 모든 검증 통과 후, 토스페이먼츠에 승인 요청 ---
        payload = {
            "paymentKey": request_data.paymentKey,
            "orderId": request_data.orderId,
            "amount": stored_amount,  # ✅ 반드시 서버에서 조회한 금액(stored_amount)을 사용!
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post("https://api.tosspayments.com/v1/payments/confirm", json=payload, headers=headers)
            response.raise_for_status()

            payment_result = response.json()
            order_id = payment_result.get("orderId")
            
            print(f"✅ [결제 승인 완료] 주문: {order_id}", payment_result)

            # --- DB 상태 업데이트 (기존 로직과 동일) ---
            update_order_status(db, order_id, "paid")

            user_id = order_in_db.get("user_id")
            plan_id = order_in_db.get("plan_id")
            update_user_plan(db, user_id, plan_id)
            
            return payment_result

    except httpx.HTTPStatusError as e:
        error_data = e.response.json()
        print(f"❌ [결제 승인 실패] {error_data}")
        raise HTTPException(status_code=e.response.status_code, detail=error_data)
    except Exception as e:
        # HTTPException이 아닌 다른 예외는 별도로 처리
        if isinstance(e, HTTPException):
            raise e
        print(f"❌ [서버 오류] {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail={"code": "UNKNOWN_ERROR", "message": str(e)})
    finally:
        db.close()


@router.post("/api/v1/payments/prepare", summary="결제 정보 사전 생성")
def prepare_payment(
    req: OrderInfoRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(lambda: SessionLocal())
):
    user_id = current_user["sub"]
    plan_id = req.plan_id
    
    order_id = f"brandie_{plan_id}_{uuid.uuid4().hex[:8]}"
    amount = get_amount_by_plan(plan_id)

    try:
        # ✅ 수정됨: SQL 문장을 text()로 감쌉니다.
        db.execute(
            text("""
            INSERT INTO orders (order_id, user_id, plan_id, logo_id, status)
            VALUES (:order_id, :user_id, :plan_id, :logo_id, :status)
            """),
            {
                "order_id": order_id,
                "user_id": user_id,
                "plan_id": plan_id,
                "logo_id": None,
                "status": "pending"
            }
        )
        db.commit()
        return {"orderId": order_id, "amount": int(amount), "orderName": "브랜디 AI 로고 플랜"}
    except Exception as e:
        print("❌ 주문 정보 사전 저장 실패:", e)
        db.rollback()
        raise HTTPException(status_code=500, detail="주문 생성에 실패했습니다.")
    finally:
        db.close()

# [추가] 결제 내역 조회 API 엔드포인트
@router.get("/api/v1/payments/history", response_model=PaymentHistoryResponse, summary="결제 내역 조회")
def get_payment_history(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
    offset: int = 0,
    limit: int = 10
):
    user_id = user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="인증 정보가 유효하지 않습니다.")

    # 'paid' 상태인 결제 내역만 조회하도록 필터 추가
    query = db.query(Order).filter(Order.user_id == user_id, Order.status == 'paid')
    
    total_count = query.count()
    
    # 실제 데이터 조회 (최신순)
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(limit).all()

    # 프론트엔드 모델에 맞게 데이터 가공
    payment_history_items = []
    for order in orders:
        payment_history_items.append(
            PaymentHistoryItem(
                orderId=order.order_id,
                amount=get_amount_by_plan(order.plan_id),
                status=order.status,
                requestedAt=order.created_at,
                itemName=f"{order.plan_id.replace('plan_', '').capitalize()} 플랜"
            )
        )

    return {"total_count": total_count, "payments": payment_history_items}


# --- 헬퍼 함수들 ---

def get_amount_by_plan(plan_id: str) -> int:
    if plan_id in ("plan_starter", "plan_basic"):
        return 13000
    elif plan_id == "plan_pro":
        return 25000
    elif plan_id == "plan_enterprise":
        return 45000
    raise ValueError(f"❌ 알 수 없는 plan_id: {plan_id}")

def update_order_status(db: Session, order_id: str, status: str):
    print(f"🔄 [DB 업데이트] 주문 {order_id} 상태를 '{status}'로 변경")
    try:
        # ✅ 수정됨: SQL 문장을 text()로 감쌉니다.
        result = db.execute(
            text("UPDATE orders SET status = :status WHERE order_id = :order_id"),
            {"status": status, "order_id": order_id}
        )
        if result.rowcount == 0:
            print(f"⚠️ 해당 order_id를 찾을 수 없음: {order_id}")
            raise ValueError("Order not found")
        db.commit()
        print("✅ 주문 상태 업데이트 완료")
    except Exception as e:
        print("❌ 주문 상태 업데이트 실패:", e)
        db.rollback()
        raise e

def update_user_plan(db: Session, user_id: str, plan_id: str):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            PLAN_MAPPING = {
                "plan_starter": "BASIC",
                "plan_basic": "BASIC",
                "plan_pro": "PRO",
                "plan_enterprise": "ENTERPRISE"
            }
            mapped_plan = PLAN_MAPPING.get(plan_id)
            if not mapped_plan:
                raise ValueError(f"Unknown plan_id: {plan_id}")
            user.plan = mapped_plan
            user.plan_changed_at = datetime.utcnow()
            db.commit()
            print(f"✅ 사용자 플랜 업데이트: {user_id} → {mapped_plan}")
    except Exception as e:
        print("❌ 사용자 플랜 업데이트 실패:", e)
        db.rollback()
        raise e