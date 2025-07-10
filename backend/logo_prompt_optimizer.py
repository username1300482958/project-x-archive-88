import os
import sys
import traceback
from typing import List, Optional
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- 장면 묘사를 상징으로 압축 ---
def compress_scene_with_gpt(user_input: str) -> str:
    try:
        system_prompt = (
            "You are a branding assistant that transforms scene descriptions into symbolic logo elements. "
            "If the input describes an action, event, or situation (e.g. 'a fox jumping over fire'), "
            "convert it into a symbolic concept suitable for a logo (e.g. 'fox and fire icon'). "
            "If already suitable, return it as-is. Output must be a short phrase."
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.2,
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("⚠️ GPT 상징 압축 실패. 원문 사용:", user_input)
        return user_input

# --- 최종 프롬프트 생성 함수 ---
def generate_dalle_prompt_with_gpt(
    brand_name: str,
    logo_style: str,
    font_style: Optional[str],
    colors: List[str],
    background: str,
    core_object: Optional[str] = None,
) -> str:
    try:
        print("🧠 GPT 기반 고도화 로고 프롬프트 생성 중...")

        system_prompt = (
            "You are a professional logo designer AI. "
            "You generate a clean, modern, 2D, flat-style logo prompt for DALL·E. "
            "Your output should describe only a symbolic logo design, suitable for business branding. "
            "Avoid anything childish, cartoony, cute, 3D, or realistic. "
            "Do not include photo elements, gradients, shadows, or background scenery. "
            "The final prompt must be one clear English sentence describing the logo image only."
        )

        # 색상
        color_part = (
            f"Use only the following hex colors: {', '.join(colors)}."
            if colors else
            "Use a clean, vibrant color palette with no more than 2 tones."
        )

        # 배경
        background_part = f"Solid {background or 'white'} background only."

        # 폰트
        font_part = f"Use a {font_style} font for brand name text." if font_style else "Use a clean, modern sans-serif font."

        # 심볼
        if core_object and core_object.strip():
            symbol_input = core_object.strip()
            compressed = compress_scene_with_gpt(symbol_input)
            symbol_part = f"Use the object '{compressed}' as the symbolic logo element."
        elif logo_style.lower() == "symbol":
            symbol_part = (
                f"Create a symbolic logo representing the brand name '{brand_name}'. "
                "If abstract, infer a metaphorical object suitable for a logo icon."
            )
        else:
            symbol_part = (
                f"Create a symbolic visual that reflects the brand name '{brand_name}' in a simple icon."
            )

        # 텍스트 포함 여부
        style_lower = logo_style.lower()
        if style_lower == "symbol":
            text_part = "Do not include any text in the logo."
        elif style_lower == "text":
            text_part = f"Only include the brand name '{brand_name}' in stylized text, no icon."
        else:  # mixed
            text_part = f"Include both a symbolic icon and the brand name '{brand_name}' in the design."

        # 최종 유저 입력 구성
        user_prompt = "\n".join([
            symbol_part,
            color_part,
            text_part,
            font_part,
            background_part
        ])

        # GPT 호출
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6,
            max_tokens=300
        )

        final_prompt = response.choices[0].message.content.strip()
        print(f"🧾 최종 DALL·E 프롬프트:\n{final_prompt}\n")
        return final_prompt

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ GPT 프롬프트 생성 실패:\n", tb)
        sys.stderr.write(tb + "\n")
        raise RuntimeError("DALL·E 프롬프트 생성 실패")