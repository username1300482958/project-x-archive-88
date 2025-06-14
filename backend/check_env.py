import os
from dotenv import load_dotenv

# ✅ 환경 변수 로드
load_dotenv()

print("AWS_ACCESS_KEY_ID:", os.getenv("AWS_ACCESS_KEY_ID"))
print("AWS_SECRET_ACCESS_KEY:", os.getenv("AWS_SECRET_ACCESS_KEY"))
print("AWS_S3_BUCKET_NAME:", os.getenv("AWS_S3_BUCKET_NAME"))
print("AWS_S3_REGION:", os.getenv("AWS_S3_REGION"))