import os
import re
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- 스타일 키워드 사전 (더욱 강화) ---
STYLE_DICTIONARY: Dict[str, str] = {
    "Minimalist": "ultra-minimalist logo, single clean icon, simple geometric shapes, thin lines, 2D vector, flat design, high contrast, heavy use of negative space, no details, no shadows, no gradients, no bold lines",
    "Modern": "modern logo, sleek lines, professional, clean, uncluttered design, functional, corporate style, no complex details, no cluttered elements",
    "Playful": "playful and whimsical cartoon style, rounded corners, fun, friendly, vibrant, energetic mood, simple illustration",
}

def _build_final_prompt(
    subject: str,
    brand_name: str,
    logo_style: str,
    style_detail: str,
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    """모든 정보를 바탕으로 최종 키워드 리스트 프롬프트를 조립하는 헬퍼 함수"""
    
    # 1. 기본 구성: 주제 + 스타일
    style_keywords = STYLE_DICTIONARY.get(style_detail.capitalize(), STYLE_DICTIONARY["Modern"])
    prompt_parts = [f"2D vector logo of '{subject}'", style_keywords]

    # 2. 텍스트 지시 추가 (폰트 스타일 반영 문제 해결)
    if logo_style.lower() in ["mixed", "text"]:
        font_instruction = f"in a '{font_style}' font" if font_style else "in a clean modern font"
        prompt_parts.append(f"with the text '{brand_name}' clearly written below, {font_instruction}")

    # 3. 색상 지시 추가
    if colors:
        colors_str = " and ".join([f"'{c}'" for c in colors])
        prompt_parts.append(f"strict color palette of only {colors_str}")
    else:
        prompt_parts.append("monochromatic black and white color scheme")

    # 4. 배경 및 금지어 추가
    background_instruction = "on a solid pure white background" if background == 'white' else "on a solid pure black background"
    negative_prompts = "NO 3d render, NO photorealistic, NO shadow, NO gradients, NO poster, NO mockup, NO extra details, simple, flat"
    prompt_parts.append(background_instruction)
    prompt_parts.append(negative_prompts)
    
    final_prompt = ", ".join(prompt_parts)
    print(f"✅ FINAL KEYWORD PROMPT: {final_prompt}")
    return final_prompt

def _get_subject_from_gpt(brand_name: str, style_detail: str) -> str:
    """GPT-4o를 사용해 브랜드 이름에 어울리는 핵심 상징물을 생성하는 헬퍼 함수"""
    print(f"🟡 No Core Object. Using GPT-4o to invent a symbol for '{brand_name}'...")
    
    system_msg = {
        "role": "system",
        "content": "You are a creative director who invents simple, iconic logo concepts. Based on the brand name and style, suggest a single, concrete object or symbol. Respond with ONLY the name of the object, in 5 words or less. For example, for 'Starlight Bakery', you might respond 'a croissant forming a crescent moon'."
    }
    user_request = f"Brand Name: '{brand_name}', Style: '{style_detail}'"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_msg, {"role": "user", "content": user_request}],
            temperature=0.7,
        )
        invented_subject = response.choices[0].message.content.strip().replace('"', '')
        print(f"✅ GPT-4o invented subject: '{invented_subject}'")
        return invented_subject
    except Exception as e:
        print(f"❌ GPT-4o subject generation failed: {e}. Falling back to brand name.")
        return brand_name # GPT 실패 시 브랜드 이름 자체를 주제로 사용

# --- 메인 함수 ---
def generate_prompt_with_gpt(
    brand_name: str,
    logo_style: str,
    style_detail: Optional[str],
    core_object: Optional[str],
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:

    # ✅ 실사 이미지 문제 해결: 스타일 선택이 없으면 'Modern'을 기본값으로 사용
    final_style_detail = style_detail if style_detail else "Modern"

    # ✅ 조건부 창의성 완벽 구현
    if core_object and core_object.strip():
        # 사용자가 핵심 상징물을 입력하면, GPT-4o를 건너뛰고 바로 프롬프트 생성
        print("✅ User provided Core Object. Bypassing GPT-4o.")
        subject = core_object
    else:
        # 사용자가 입력하지 않았을 때만, GPT-4o를 호출하여 아이디어(subject)를 얻음
        subject = _get_subject_from_gpt(brand_name, final_style_detail)
        
    # 최종적으로 결정된 subject와 나머지 정보로 프롬프트를 조립
    return _build_final_prompt(
        subject=subject,
        brand_name=brand_name,
        logo_style=logo_style,
        style_detail=final_style_detail,
        font_style=font_style,
        colors=colors,
        background=background
    )