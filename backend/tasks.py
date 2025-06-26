# backend/tasks.py

# --- 필요한 모든 '부품'과 '도구'들을 가져옵니다 ---
from celery_worker import celery_app
from utils_watermark import apply_watermark_optimized
from upscale_utils import upscale_image_with_replicate # 기존 upscale 함수
from s3_utils import s3_client, AWS_S3_BUCKET_NAME # 기존 S3 클라이언트 정보
# TODO: 최종 이미지를 S3에 올리는 함수를 s3_utils.py에서 가져와야 합니다.
# from s3_utils import upload_final_image_to_s3 
from database import get_db
# TODO: DB 상태를 업데이트하는 함수를 만들어 가져와야 합니다.
# from crud import update_logo_status 

import requests
from PIL import Image
import io
from urllib.parse import urlparse

@celery_app.task(bind=True) # bind=True는 작업 자체의 정보를 self 인자로 받기 위함입니다.
def process_high_res_image(self, original_s3_url: str, logo_id: int):
    """
    원본 S3 이미지를 받아 -> 업스케일 -> 워터마크 -> 최종 S3 저장 -> DB 업데이트
    이 모든 과정을 처리하는 완전한 작업입니다.
    """
    # with get_db() as db: # 작업 내에서 새로운 DB 세션을 열어 사용합니다.
    try:
        # --- 1. S3에서 원본 이미지 가져오기 (download_upscaled.py 로직) ---
        parsed_url = urlparse(original_s3_url)
        object_key = parsed_url.path.lstrip('/')
        
        in_mem_file = io.BytesIO()
        s3_client.download_fileobj(AWS_S3_BUCKET_NAME, object_key, in_mem_file)
        in_mem_file.seek(0)
        
        # --- 2. Replicate로 업스케일링 요청 (download_upscaled.py 로직) ---
        # 이 함수는 업스케일된 이미지의 URL을 반환합니다.
        upscaled_url = upscale_image_with_replicate(in_mem_file, scale=2)
        if not upscaled_url:
            raise ValueError("Replicate 업스케일링에 실패했습니다.")

        # --- 3. 업스케일된 이미지를 Replicate URL에서 다운로드 ---
        response = requests.get(upscaled_url, timeout=60)
        response.raise_for_status()
        upscaled_image = Image.open(io.BytesIO(response.content))
        
        # --- 4. 다운로드한 고화질 이미지에 워터마크 적용 ---
        final_image = apply_watermark_optimized(upscaled_image)
        
        # --- 5. 최종 결과물을 S3에 다시 업로드 ---
        final_buffer = io.BytesIO()
        final_image.save(final_buffer, format='PNG')
        final_buffer.seek(0)
        
        # TODO: 이 부분은 실제 S3 업로드 함수로 교체해야 합니다.
        # final_s3_key = f"highres/{logo_id}.png"
        # final_s3_url = upload_final_image_to_s3(final_buffer, final_s3_key)
        
        # --- 6. DB에 최종 결과물 URL과 상태 업데이트 ---
        # TODO: 이 부분은 실제 DB 업데이트 함수로 교체해야 합니다.
        # update_logo_status(db, logo_id, "completed", final_s3_url)
        
        return f"Logo {logo_id} processed successfully."

    except Exception as e:
        # --- 7. 에러 발생 시 DB에 실패 상태 기록 ---
        # TODO: 이 부분은 실제 DB 에러 처리 함수로 교체해야 합니다.
        # update_logo_status(db, logo_id, "failed")
        print(f"Error processing logo {logo_id}: {e}")
        # Celery가 재시도하도록 예외를 다시 발생시킵니다.
        raise self.retry(exc=e, countdown=60, max_retries=3)