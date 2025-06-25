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

def upscale_image_with_replicate(local_image_path: str, scale: int = 2) -> str:
    """
    1) 로컬 이미지 파일을 Replicate Real-ESRGAN 모델로 업스케일링
    2) 업스케일된 이미지를 임시로 다운로드
    3) S3에 업로드 후 presigned URL 반환

    Returns:
        presigned_url (str)
    """
    # 파일 존재 여부
    if not os.path.exists(local_image_path):
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {local_image_path}")

    # 3) Replicate API 호출
    with open(local_image_path, "rb") as img:
        result = replicate_client.run(
            "replicate/real-esrgan:42fed1c4974146d4d2414e2be2c5236e7a8c9053", # 👈 이 새로운 주소로 교체합니다.
            input={ "image": img, "scale": scale, "face_enhance": False },
        )

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

    # 7) presigned URL 생성
    presigned = generate_presigned_url_from_s3_url(s3_url)
    if not presigned:
        # fallback: 공개 S3 URL 반환
        presigned = s3_url

    # 8) 임시 파일 제거
    try:
        os.remove(tmp_path)
    except Exception:
        pass

    return presigned