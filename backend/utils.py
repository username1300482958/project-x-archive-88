from backend.database import SessionLocal
from backend.models import ErrorLog, User
from fastapi import Request

def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        # 여러 프록시를 거친 경우, 첫 번째 IP가 클라이언트 IP
        return x_forwarded_for.split(",")[0].strip()
    return request.client.host

def log_error(user_id: str, context: str, message: str, stack_trace: str = None):
    db = SessionLocal()
    try:
        error_log = ErrorLog(
            user_id=user_id,
            context=context,
            message=message,
            stack_trace=stack_trace
        )
        db.add(error_log)
        db.commit()
    except Exception as e:
        print("Error logging failed:", e)
    finally:
        db.close()

def get_user_plan(user_id: str) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        return (user.plan or "FREE").upper() if user else "FREE"
    finally:
        db.close()