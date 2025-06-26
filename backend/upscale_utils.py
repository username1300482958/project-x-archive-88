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
    [최종 디버깅 완료] Replicate가 반환하는 'FileOutput' 객체를 직접 처리하여
    업스케일링을 수행하고 S3 presigned URL을 반환합니다.
    """
    print(f"🚀 Replicate에 업스케일링 요청 시작 (파일 데이터 직접 전달)...")
    
    # 1. replicate.run()을 호출하여 'FileOutput' 객체를 받습니다.
    file_output = replicate_client.run(
        "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
        input={
            "image": image_file_object,
            "scale": scale
        }
    )
    print("✅ Replicate 작업 완료, 'FileOutput' 객체 수신")

    # 2. 'FileOutput' 객체에서 .read() 메소드를 호출하여 이미지 데이터(bytes)를 직접 추출합니다.
    #    이전의 모든 복잡한 로직이 이 한 줄로 해결됩니다.
    image_bytes = file_output.read()

    # 3. 추출한 이미지 데이터를 임시 파일에 씁니다.
    tmp_dir = tempfile.gettempdir()
    tmp_filename = f"upscaled_{uuid4().hex[:8]}.png"
    tmp_path = os.path.join(tmp_dir, tmp_filename)
    with open(tmp_path, "wb") as f:
        f.write(image_bytes)

    # 4. 이후 로직은 S3 업로드, presigned URL 생성으로 동일합니다.
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

    print("✅ 모든 업스케일링 및 업로드 과정 성공")
    return presigned