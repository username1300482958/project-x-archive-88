import os
import traceback
import sys
from typing import List, Optional
from openai import OpenAI

# --- OpenAI 클라이언트 초기화 ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- GPT 기반 DALL·E 프롬프트 생성 ---
def generate_dalle_prompt_with_gpt(
    brand_name: str,
    logo_style: str,
    font_style: Optional[str],
    colors: List[str],
    background: str,
    core_object: Optional[str] = None  # ✅ 핵심 상징물 필드 추가
) -> str:
    try:
        print("🧠 GPT 기반 고도화 로고 프롬프트 생성 중...")

        # 시스템 역할 지정
        system_prompt = (
            "You are a professional logo designer assistant. "
            "Based on the inputs below, generate a high-quality prompt for DALL·E to create a clean, modern, iconic logo. "
            "The design should be minimal, 2D, flat, and symbolic. "
            "Avoid realistic styles, gradients, shadows, photographic effects, or cute characters. "
            "The output must be a single English sentence describing the image for DALL·E."
        )

        # 핵심 상징물이 제공된 경우 우선 사용
        if core_object and core_object.strip():
            symbol_part = f"Use the following object as the main logo symbol: '{core_object.strip()}'."
        else:
            symbol_part = f"Suggest and use a symbolic visual based on the brand name '{brand_name}'."

        # 색상 정보 구성
        color_part = f"Use a color palette limited to {', '.join(colors)}." if colors else "Use a clean, vibrant color palette."

        # 텍스트 포함 여부
        if logo_style.lower() in ["mixed", "text"]:
            text_part = f"Include the brand name text '{brand_name}' in a {font_style or 'rounded sans-serif'} font."
        else:
            text_part = "Do not include any text."

        # 배경 구성
        background_part = f"Background: solid {background or 'white'}."

        # 최종 유저 입력 메시지 구성
        user_prompt = "\n".join([
            symbol_part,
            color_part,
            text_part,
            background_part
        ])

        # GPT 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=200
        )

        # 결과 추출
        prompt = response.choices[0].message.content.strip()
        print(f"🧾 최종 DALL·E 프롬프트:\n{prompt}\n")
        return prompt

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ GPT 프롬프트 생성 실패:\n", tb)
        sys.stderr.write(tb + "\n")
        raise RuntimeError("DALL·E 프롬프트 생성 실패")