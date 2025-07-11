import os
import sys
import traceback
from typing import List, Dict, Optional
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_professional_logo_concept(core_object: str, brand_name: str = None, color: str = None) -> Dict[str, str]:
    """
    사용자 입력(핵심 오브젝트, 브랜드명, 컬러 등)을 전문 로고 컨셉으로 변환.
    프롬프트에서 HEX+영문컬러명을 동시에 요구.
    """
    try:
        system_prompt = """You are a world-class logo design consultant for high-end brands.
Your role is to convert user concepts into a professional logo SYMBOL ONLY (no text, no scene).
Use iconic, memorable, simple shapes only. NEVER add letters or words.

--- Your output format (JSON) ---
{
  "symbol_concept": "Describe a single iconic symbol for the logo, under 15 words. Example: 'A bold yellow banana curving around a soccer ball'",
  "color_strategy": "If user gives a color, always use both the HEX code and color name, e.g. 'FFD700 (yellow)'. Only use this color for the main symbol. Never use other colors.",
  "style": "flat vector, ultra minimal, perfect symmetry, commercial design",
  "brand_personality": "3 words for brand feel (e.g. energetic, modern, clean)"
}

--- INSTRUCTIONS ---
- Focus on SYMBOL. Never output text, signature, scene, or letters.
- Use only the main HEX color given by the user. If none, propose a single solid color.
- Always explain colors as both HEX and color name.
- Output must be valid JSON.
"""

        user_message = f"Core object: {core_object}\n"
        if brand_name:
            user_message += f"Brand name: {brand_name}\n"
        if color:
            user_message += f"Main color: {color}\n"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.25,
            max_tokens=256
        )

        import json
        try:
            result = json.loads(response.choices[0].message.content.strip())
            return result
        except Exception:
            # JSON 파싱 실패시 심볼/컬러만 추출
            text = response.choices[0].message.content.strip()
            return {
                "symbol_concept": text[:80],
                "color_strategy": color or "single solid color",
                "style": "flat vector, ultra minimal, perfect symmetry, commercial design",
                "brand_personality": "modern, clean, bold"
            }
    except Exception as e:
        print(f"⚠️ 로고 컨셉 생성 실패: {e}")
        return {
            "symbol_concept": core_object,
            "color_strategy": color or "single solid color",
            "style": "flat vector, ultra minimal, perfect symmetry, commercial design",
            "brand_personality": "modern, clean, bold"
        }

def generate_premium_logo_prompt(
    core_object: str,
    colors: List[str] = None,
    brand_name: str = None
) -> str:
    """
    심볼형 로고 프롬프트를 생성 (HEX+ColorName, 네거티브 강화)
    """
    try:
        # 색상 (최대 1개만)
        color_hex = colors[0] if colors and len(colors) > 0 else None

        # GPT에서 symbol_concept, color_strategy 모두 뽑음
        logo_concept = create_professional_logo_concept(core_object, brand_name, color_hex)
        symbol = logo_concept["symbol_concept"]
        color = logo_concept["color_strategy"]
        style = logo_concept["style"]
        brand_personality = logo_concept["brand_personality"]

        # DALL-E 프롬프트 강화: 심볼/색상 명시, 네거티브 반복, HEX+ColorName 병기
        final_prompt = (
            f"Flat vector logo icon: {symbol}, "
            f"main color: {color}. "
            f"{style}, {brand_personality} style, "
            "no text, no letters, no words, no signature, no brand name, "
            "no extra colors, no gradients, no shadows, no 3d, no photorealism, "
            "minimal, commercial, scalable. On pure white background."
        )
        # 네거티브 반복 삽입 (텍스트/워드마크 오염 방지 시도)
        final_prompt += " --no text, no words, no letters, no font, no signature, no watermark, no complex illustration."

        print(f"🔧 최종 로고 프롬프트:\n{final_prompt}\n")
        return final_prompt

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ 로고 프롬프트 생성 실패:\n{tb}")
        sys.stderr.write(tb + "\n")
        raise RuntimeError("로고 프롬프트 생성 실패")

def generate_logo_variations(core_object: str, colors: List[str] = None, brand_name: str = None) -> List[str]:
    """
    색상별 심볼 로고 프롬프트 (스타일 변형 없음)
    """
    variations = []
    color_list = colors if colors else [None]
    for color in color_list:
        try:
            prompt = generate_premium_logo_prompt(core_object, [color] if color else None, brand_name)
            variations.append({
                "color": color,
                "prompt": prompt
            })
        except Exception as e:
            print(f"⚠️ {color} 색상 버전 생성 실패: {e}")
    return variations

# === 테스트 코드 ===
if __name__ == "__main__":
    test_core_object = "banana kick"
    test_brand = "BananaKick"
    test_colors = ["FFD700", "0066FF"]

    print("=== 프리미엄 로고 생성 테스트 ===")
    try:
        logo_prompt = generate_premium_logo_prompt(
            core_object=test_core_object,
            colors=test_colors,
            brand_name=test_brand
        )
        print(f"생성된 프롬프트: {logo_prompt}")

        print("\n=== 색상 변형 생성 ===")
        variations = generate_logo_variations(test_core_object, test_colors, test_brand)
        for i, variation in enumerate(variations):
            print(f"\n{i+1}. {variation['color'] or 'DEFAULT'} 컬러:")
            print(variation['prompt'])

    except Exception as e:
        print(f"테스트 실패: {e}")