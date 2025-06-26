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

# 2) Replicate 클라이언트 초기화
replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

def upscale_image_with_replicate(image_file_object, scale: int = 2) -> str:
    """
    [진짜 최종 완성본] Replicate가 URL을 반환하든, 이미지 데이터(bytes)를 반환하든
    모든 상황에 대응하여 업스케일링을 수행하고 S3 presigned URL을 반환합니다.
    """
    print(f"🚀 Replicate에 업스케일링 요청 시작 (파일 데이터 직접 전달)...")
    
    # 1. replicate.run()을 호출하고 그 결과를 'iterator'로 받습니다.
    #    이전처럼 list()로 바로 감싸지 않습니다.
    result_iterator = replicate_client.run(
        "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
        input={
            "image": image_file_object,
            "scale": scale
        }
    )
    print("✅ Replicate 작업 완료, 결과 데이터 수신")

    # 2. iterator에서 첫 번째 결과물을 추출합니다.
    first_result = next(result_iterator, None)
    if first_result is None:
        raise ValueError("Replicate로부터 아무런 결과도 받지 못했습니다.")

    image_bytes = None
    # 3. 결과물의 타입에 따라 분기하여 처리합니다.
    #    결과가 URL(문자열)인 경우
    if isinstance(first_result, str) and first_result.startswith("http"):
        print("✅ Replicate가 URL을 반환했습니다. 해당 URL에서 이미지를 다운로드합니다.")
        resp = requests.get(first_result) # stream=True는 content 사용 시 불필요
        if resp.status_code != 200:
            raise RuntimeError(f"업스케일된 이미지 다운로드 실패: HTTP {resp.status_code}")
        image_bytes = resp.content
    #    결과가 이미지 데이터(바이트)인 경우
    elif isinstance(first_result, bytes):
        print("✅ Replicate가 이미지 데이터를 직접 반환했습니다.")
        image_bytes = first_result
    #    둘 다 아닌 경우
    else:
        raise ValueError(f"예상치 못한 Replicate 응답 타입: {type(first_result)}")

    # 4. 최종적으로 얻은 image_bytes를 임시 파일에 씁니다.
    tmp_dir = tempfile.gettempdir()
    tmp_filename = f"upscaled_{uuid4().hex[:8]}.png"
    tmp_path = os.path.join(tmp_dir, tmp_filename)
    with open(tmp_path, "wb") as f:
        f.write(image_bytes)

    # 5. 이후 로직은 S3 업로드, presigned URL 생성으로 동일합니다.
    object_key = f"upscaled/{tmp_filename}"
    s3_url = upload_to_s3(tmp_path, object_key)
    if not s3_url:
        raise RuntimeError("❌ S3 업로드에 실패했습니다.")

    presigned = generate_presigned_url_from_s3_url(
        s3_url,
        download_name=tmp_filename
    )
    if not presigned:
        presigned = s3_url

    try:
        os.remove(tmp_path)
    except Exception:
        pass

    return presigned