# backend/config.py (수정된 최종 코드)

import os
from dotenv import load_dotenv

# .env 파일이 backend 폴더의 부모 폴더(프로젝트 루트)에 있다고 가정
# 정확한 경로를 위해 이 방식을 사용하는 것이 더 안정적입니다.
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)

# --- 공통 설정 변수 ---
# ✅ 여기에 BASE_BACKEND_URL 정의를 추가합니다.
BASE_BACKEND_URL = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")

# 기존에 있던 다른 키들도 여기에 계속 추가하면 됩니다.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in .env")