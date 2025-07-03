from openai import OpenAI
import os
import uuid
import base64
import traceback
import sys

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_logo_image(prompt: str) -> str:
    try:
        print("🧪 generate_logo_image 호출됨, prompt:", prompt)

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            n=1,
            response_format="b64_json",
        )

        image_b64 = response.data[0].b64_json

        filename = f"{uuid.uuid4().hex}.png"
        image_path = f"generated_openai_logos/{filename}"
        os.makedirs("generated_openai_logos", exist_ok=True)

        with open(image_path, "wb") as f:
            f.write(base64.b64decode(image_b64))

        print("✅ 이미지 생성 완료, 저장 경로:", image_path)
        return image_path

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ OpenAI 로고 생성 실패:\n", tb)
        sys.stderr.write(tb + "\n")
        raise RuntimeError(f"OpenAI 이미지 생성 실패: {str(e)}")  # 🔥 예외 직접 던짐