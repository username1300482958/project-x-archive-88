import boto3
import os
import time
import logging  # 추가: 로깅용
from dotenv import load_dotenv
from botocore.exceptions import NoCredentialsError
from .utils import log_error  # log_error 함수 import

# 환경 변수 로드 (.env 파일에 AWS 관련 정보가 있어야 함)
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
AWS_S3_REGION = os.getenv("AWS_S3_REGION")

# S3 클라이언트 생성
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_S3_REGION
)

def delete_from_s3(s3_url):
    """
    S3에서 특정 파일을 삭제하는 함수
    """
    try:
        bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        region = os.getenv("AWS_S3_REGION")
        object_key = s3_url.split(f"https://{bucket_name}.s3.{region}.amazonaws.com/")[-1]
        s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        print(f"✅ S3에서 삭제 완료: {s3_url}")
    except NoCredentialsError:
        print("⚠️ AWS 자격 증명이 설정되지 않았습니다.")
    except Exception as e:
        print(f"⚠️ S3 삭제 오류: {e}")

def generate_presigned_url_from_s3_url(s3_url, expiration=3600, download_name=None):
    """
    저장된 s3_url을 파싱해서 Presigned URL을 생성하여 반환합니다.
    [수정] download_name 파라미터를 추가하여 파일 다운로드를 강제할 수 있습니다.
    """
    prefix = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_S3_REGION}.amazonaws.com/"
    if s3_url.startswith(prefix):
        object_key = s3_url[len(prefix):]
        
        # 👇 이 부분이 핵심입니다.
        params = {'Bucket': AWS_S3_BUCKET_NAME, 'Key': object_key}
        if download_name:
            # download_name이 제공되면, 브라우저에게 다운로드하라는 신호를 보냅니다.
            params['ResponseContentDisposition'] = f'attachment; filename="{download_name}"'
        # 👆 여기까지가 수정된 부분입니다.

        try:
            url = s3_client.generate_presigned_url(
                'get_object',
                Params=params, # 수정된 params 사용
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            print(f"❌ Presigned URL 생성 오류: {e}")
            return s3_url
    return s3_url

def upload_to_s3(file_path, object_name, user_id=None):
    """
    [최종 수정됨] 주어진 파일을 S3에 업로드하고, 업로드 성공 여부를 '검증'한 뒤 URL을 반환합니다.
    """
    max_retries = 3
    retry_delay = 2  # 초 단위 딜레이
    last_error = None

    for attempt in range(max_retries):
        try:
            # 1. 파일 업로드 시도
            s3_client.upload_file(file_path, AWS_S3_BUCKET_NAME, object_name, ExtraArgs={"ContentType": "image/png"})
            
            # 👇 [핵심 수정] 업로드 후, 해당 파일이 정말 존재하는지 확인(Verify)합니다.
            print(f"... S3 업로드 후 검증 시도: {object_name}")
            s3_client.head_object(Bucket=AWS_S3_BUCKET_NAME, Key=object_name)
            print("✅ S3 업로드 검증 성공!")

            # 2. 검증까지 성공해야만 진짜 URL을 반환합니다.
            s3_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_S3_REGION}.amazonaws.com/{object_name}"
            return s3_url

        except Exception as e:
            last_error = e
            logging.error(f"❌ S3 업로드/검증 실패 (시도 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries -1:
                time.sleep(retry_delay)
            else:
                # 최종 실패 시 에러 로그 기록
                if user_id:
                    log_error(
                        user_id=user_id,
                        context="S3 Upload",
                        message=f"S3 업로드 최종 실패: {str(last_error)}",
                        stack_trace=str(last_error)
                    )
    
    # 3. 모든 시도가 실패하면 None을 반환합니다.
    return None