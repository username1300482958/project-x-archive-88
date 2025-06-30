# upscale_utils.py (진단 완료 최종본2)

import os
import replicate
from replicate.exceptions import ReplicateError

# --- 이 부분은 기존과 동일하게 유지 ---
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise RuntimeError("❌ REPLICATE_API_TOKEN 환경변수가 설정되지 않았습니다.")

replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)
# --- 여기까지는 기존과 동일 ---


def get_replicate_upscale_url(image_url: str, scale: int = 2) -> str:
    """
    [진단 완료 최종본] Replicate가 반환하는 FileOutput 객체에서
    URL 속성을 직접 추출하여 반환합니다.
    """
    print(f"🚀 Replicate에 업스케일링 요청 시작 (URL 전달 방식)...")

    try:
        # 1. replicate.run()을 호출하여 결과 객체를 받습니다.
        file_output = replicate_client.run(
            "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
            input={
                "image": image_url,
                "scale": scale
            }
        )
        
        # ▼▼▼▼▼▼▼▼▼▼ [최종 핵심 수정] ▼▼▼▼▼▼▼▼▼▼
        # 2. 결과 객체의 URL을 문자열로 변환하여 직접 사용합니다.
        #    이전의 모든 복잡한 타입 검사 로직이 필요 없어집니다.
        final_url = str(file_output)
        
        # 3. URL이 정상적인지 마지막으로 확인합니다.
        if not final_url.startswith("http"):
            raise ValueError(f"결과물에서 유효한 URL을 찾을 수 없습니다: {final_url}")
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    except ReplicateError as e:
        # Replicate API 자체에서 발생한 에러를 좀 더 명확하게 로깅
        print(f"❌ Replicate API 에러 발생: {e}")
        raise RuntimeError(f"Replicate API 에러: {e}") from e
    except Exception as e:
        # 기타 예외 처리
        print(f"❌ 업스케일링 중 알 수 없는 에러 발생: {e}")
        raise RuntimeError(f"업스케일링 중 알 수 없는 에러: {e}") from e

    print(f"✅ Replicate 작업 완료, 결과 URL 수신: {final_url}")
    return final_url