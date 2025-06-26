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

# 👇 함수가 이제 image_url 대신 image_file_object를 받도록 변경합니다.
def upscale_image_with_replicate(image_file_object, scale: int = 2) -> str:
    """
    [최종 수정됨] 파일 객체를 직접 받아 Replicate Real-ESRGAN 모델로 업스케일링
    """
    print(f"🚀 Replicate에 업스케일링 요청 시작 (파일 데이터 직접 전달)...")
    
    # 👇 이제 URL이 아닌, 전달받은 파일 객체를 바로 input으로 사용합니다.
    result = list(replicate_client.run(
        "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
        input={
            "image": image_file_object,
            "scale": scale
        }
    ))
    print("✅ Replicate 작업 완료, 결과 URL 수신")


    # 결과에서 URL 추출
    output_url = result[0] if isinstance(result, list) else result
    if not (isinstance(output_url, str) and output_url.startswith("http")):
        raise ValueError(f"잘못된 Replicate 응답 URL: {output_url}")

    # 4) 업스케일된 이미지 다운로드
    resp = requests.get(output_url, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f"업스케일된 이미지 다운로드 실패: HTTP {resp.status_code}")

    # 5) 임시 로컬에 저장
    tmp_dir = tempfile.gettempdir()
    tmp_filename = f"upscaled_{uuid4().hex[:8]}.png"
    tmp_path = os.path.join(tmp_dir, tmp_filename)
    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)

    # 6) S3에 업로드
    #    object_key 예: "upscaled/{파일명}"
    object_key = f"upscaled/{tmp_filename}"
    s3_url = upload_to_s3(tmp_path, object_key)
    if not s3_url:
        raise RuntimeError("❌ S3 업로드에 실패했습니다.")

    # 7) presigned URL 생성 (다운로드 강제 옵션 추가)
    # 👇 tmp_filename 변수를 사용하여 다운로드 파일명을 지정해줍니다.
    presigned = generate_presigned_url_from_s3_url(
        s3_url,
        download_name=tmp_filename
    )
    if not presigned:
        # fallback: 공개 S3 URL 반환
        presigned = s3_url

    # 8) 임시 파일 제거
    try:
        os.remove(tmp_path)
    except Exception:
        pass

    return presigned