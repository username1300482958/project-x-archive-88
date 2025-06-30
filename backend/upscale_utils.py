# upscale_utils.py (진단용 코드)

import os
import replicate

# --- 이 부분은 기존과 동일하게 유지 ---
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
if not REPLICATE_API_TOKEN:
    raise RuntimeError("❌ REPLICATE_API_TOKEN 환경변수가 설정되지 않았습니다.")

replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)
# --- 여기까지는 기존과 동일 ---


def get_replicate_upscale_url(image_url: str, scale: int = 2) -> str:
    """
    [진단용] Replicate가 반환하는 결과물의 타입을 정확히 파악하기 위한 코드입니다.
    """
    print("🕵️  [진단 모드] 업스케일링 요청 시작...")

    output = None # 변수 초기화
    try:
        output = replicate_client.run(
            "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
            input={
                "image": image_url,
                "scale": scale
            }
        )
        
        # --- Start of Diagnostic Block ---
        print("🕵️  [진단] Replicate로부터 받은 결과물(output)을 정밀 분석합니다.")
        print(f"🕵️  [진단] 1. 결과물의 타입(type): {type(output)}")
        print(f"🕵️  [진단] 2. 결과물을 문자열로 변환 시도(str): {str(output)}")
        
        is_list = isinstance(output, list)
        print(f"🕵️  [진단] 3. 결과물이 리스트인가? (isinstance): {is_list}")
        
        if is_list and output:
            first_item = output[0]
            print(f"🕵️  [진단] 3a. (리스트인 경우) 첫 번째 항목의 타입: {type(first_item)}")
            print(f"🕵️  [진단] 3b. (리스트인 경우) 첫 번째 항목의 값: {first_item}")

        try:
            output_as_list = list(output)
            print(f"🕵️  [진단] 4. 결과물을 리스트로 강제 변환 시도(list()): {output_as_list}")
            if output_as_list:
                first_item_from_list = output_as_list[0]
                print(f"🕵️  [진단] 4a. (강제 변환 후) 첫 번째 항목의 타입: {type(first_item_from_list)}")
                print(f"🕵️  [진단] 4b. (강제 변환 후) 첫 번째 항목의 값: {first_item_from_list}")
        except Exception as e:
            print(f"🕵️  [진단] 4. 리스트로 강제 변환 중 에러 발생: {e}")
        
        print("🕵️  [진단] 정밀 분석 완료.")
        # --- End of Diagnostic Block ---

        # 에러를 발생시키기 위해 임시로 항상 실패하도록 만듭니다.
        raise RuntimeError("진단 완료. 로그를 확인해주세요.")

    except Exception as e:
        print(f"💥 최종 에러 발생. 에러: {e}")
        # 디버깅을 위해 받은 원본 output이 있다면 함께 출력
        if output is not None:
            print(f"💥 에러 발생 시점의 output 변수 내용: {output}")
        raise e