# upscale_utils.py (진짜 최종본)

import os
import replicate

# --- 이 부분은 그대로 유지 ---
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise RuntimeError("❌ REPLICATE_API_TOKEN 환경변수가 설정되지 않았습니다.")

replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)
# --- 여기까지는 그대로 유지 ---


def get_replicate_upscale_url(image_url: str, scale: int = 2) -> str:
    """
    [최종본] Replicate를 실행하고, 이터레이터 등 다양한 결과 형태에 모두 대응하여 URL을 추출합니다.
    이 함수는 서버의 메모리를 거의 사용하지 않습니다.
    """
    print(f"🚀 Replicate에 업스케일링 요청 시작 (URL 전달 방식)...")

    # 1. replicate.run()을 호출하여 결과물(이터레이터 또는 다른 객체)을 받습니다.
    output = replicate_client.run(
        "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
        input={
            "image": image_url,
            "scale": scale
        }
    )
    
    # ▼▼▼▼▼▼▼▼▼▼ [핵심 수정: 더 튼튼한 방식] ▼▼▼▼▼▼▼▼▼▼
    final_url = ""

    # 2. 결과가 어떤 형태(이터레이터, 리스트 등)로 오더라도 리스트로 변환하여 첫 번째 항목을 안전하게 추출합니다.
    try:
        # 대부분의 경우 이 코드가 실행됩니다.
        output_list = list(output)
        if output_list:
            final_url = output_list[0]
    except TypeError:
        # 만약 결과가 이터레이터나 리스트가 아닌 일반 객체일 경우, 문자열로 변환을 시도합니다.
        final_url = str(output)

    # 3. 최종적으로 URL이 정상적인 문자열 형태인지 확인합니다.
    if isinstance(final_url, str) and final_url.startswith("http"):
        # 성공!
        print(f"✅ Replicate 작업 완료, 결과 URL 수신: {final_url}")
        return final_url
    else:
        # 실패 시, 받은 원본(output)을 그대로 로그에 남겨서 디버깅을 돕습니다.
        print(f"❌ Replicate에서 처리할 수 없는 결과 형식을 반환했습니다: {output}")
        raise RuntimeError("Replicate에서 예상치 못한 결과 형식을 반환했습니다.")
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲
