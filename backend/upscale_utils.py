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
    [최종본] Replicate를 실행하고, 리스트 등 다양한 결과 형태에 모두 대응하여 URL을 추출합니다.
    이 함수는 서버의 메모리를 거의 사용하지 않습니다.
    """
    print(f"🚀 Replicate에 업스케일링 요청 시작 (URL 전달 방식)...")

    # 1. replicate.run()을 호출하여 결과물을 'output' 변수에 담습니다.
    output = replicate_client.run(
        "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
        input={
            "image": image_url,
            "scale": scale
        }
    )
    
    final_url = None

    # 2. Replicate 결과가 리스트일 경우, 첫 번째 요소를 URL로 사용합니다.
    if isinstance(output, list) and output:
        final_url = output[0]
    # 3. 결과가 그냥 문자열일 경우, 그것을 URL로 사용합니다.
    elif isinstance(output, str):
        final_url = output

    # 4. 최종적으로 URL이 정상적인 형태인지 다시 한번 확인합니다.
    if not final_url or not final_url.startswith("http"):
        # 문제가 있을 경우, 받은 원본(output)을 그대로 로그에 남깁니다.
        print(f"❌ Replicate 결과가 예상과 다릅니다: {output}")
        raise RuntimeError("Replicate에서 예상치 못한 결과 형식을 반환했습니다.")

    print(f"✅ Replicate 작업 완료, 결과 URL 수신: {final_url}")
    
    # 5. 추출한 최종 URL을 반환합니다.
    return final_url