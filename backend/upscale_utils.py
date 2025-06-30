import os
import tempfile
import requests
import replicate
from uuid import uuid4
from .s3_utils import upload_to_s3, generate_presigned_url_from_s3_url

# 1) .env에 REPLICATE_API_TOKEN 설정 여부 확인
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise RuntimeError("❌ REPLICATE_API_TOKEN 환경변수가 설정되지 않았습니다.")

# Replicate 클라이언트 초기화
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

# ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼
# --- 새로운 메모리 최적화 함수 ---
def get_replicate_upscale_url(image_url: str, scale: int = 2) -> str:
    """
    [최적화 완료] Replicate를 실행하고, 결과 이미지의 URL만 즉시 반환합니다.
    이 함수는 서버의 메모리를 거의 사용하지 않습니다.
    """
    print(f"🚀 Replicate에 업스케일링 요청 시작 (URL 전달 방식)...")

    # 1. replicate.run()을 호출하여 결과물(이미지 URL)을 직접 받습니다.
    #    이전처럼 파일을 다운로드하고 처리하는 과정이 모두 생략됩니다.
    output_url = replicate_client.run(
        "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
        input={
            "image": image_url, # 이제 이곳에는 S3의 presigned URL이 들어옵니다.
            "scale": scale
        }
    )
    
    # 2. 결과가 올바른 URL 형태인지 간단히 확인합니다.
    if not isinstance(output_url, str) or not output_url.startswith("http"):
        # 만약 결과가 리스트 형태 등 예상과 다를 경우 에러 처리
        print(f"❌ Replicate 결과가 예상과 다릅니다: {output_url}")
        raise RuntimeError("Replicate에서 예상치 못한 결과 형식을 반환했습니다.")

    print(f"✅ Replicate 작업 완료, 결과 URL 수신: {output_url}")
    
    # 3. 받은 URL을 그대로 반환합니다.
    return output_url