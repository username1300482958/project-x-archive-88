# backend/celery_worker.py

from celery import Celery
import os

# Render 환경에서는 이 URL이 자동으로 설정됩니다.
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0') 

celery_app = Celery(
    'tasks',
    broker=REDIS_URL,
    backend=REDIS_URL
)

# ❗️[수정] Celery가 현재 디렉토리에서 'tasks.py'라는 파일을 찾도록 설정합니다.
# 'app' 폴더가 없으므로 ['tasks'] 라고만 지정합니다.
celery_app.autodiscover_tasks(['tasks'])