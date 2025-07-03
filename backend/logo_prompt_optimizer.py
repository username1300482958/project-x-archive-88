import os
import re
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

# ✨ 최종 전략: GPT-4o가 직접 스타일 키워드를 생성하도록 역할을 부여
def _get_style_keywords_from_gpt(style_detail: str) -> str:
    """GPT-4o를 '스타일 전문가'로 활용하여 최적의 키워드 뭉치를 생성"""
    print(f"✅'{style_detail}' 스타일에 대한 전문 키워드 생성 시도...")
    
    system_msg = {
        "role": "system",
        "content": """
You are a professional logo design consultant. Your task is to take a single style name (e.g., 'Minimalist') and expand it into a powerful, comma-separated list of DALL-E 3 keywords to create a high-quality logo.

**Crucial Rules:**
1.  **Always include 'logo design' and 'vector logo'.** This is mandatory.
2.  Use strong, direct, and effective keywords.
3.  Include negative keywords (e.g., 'no 3d, no photo') to prevent unwanted styles.
4.  Your entire response must be ONLY the comma-separated list of keywords. No conversational text.
"""
    }
    user_request = f"Style: '{style_detail}'"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_msg, {"role": "user", "content": user_request}],
            temperature=0.2, # 일관된 키워드 생성을 위해 온도를 낮춤
        )
        keywords = response.choices[0].message.content.strip().replace('"', '')
        print(f"✅ GPT-4o가 생성한 스타일 키워드: {keywords}")
        return keywords
    except Exception as e:
        print(f"❌ GPT-4o 키워드 생성 실패: {e}. 기본값으로 대체합니다.")
        # GPT-4o 실패 시 사용할 안전한 기본값
        if style_detail == "Minimalist":
            return "minimalist logo design, vector logo, simple icon, clean lines, flat, 2D, negative space, no 3d, no shadow"
        else: # Modern
            return "modern logo design, vector logo, sleek, professional, corporate, clean, flat, 2D, no 3d, no shadow"

def _get_subject_from_gpt(brand_name: str, style_detail: str) -> str:
    """(기존과 동일) 브랜드 이름에서 핵심 상징물 유추"""
    # ... (이전 답변의 _get_subject_from_gpt 함수 코드는 변경 없음) ...
    print(f"🟡 No Core Object. Using GPT-4o to invent a symbol for '{brand_name}'...")
    system_msg = { "role": "system", "content": "You are a creative director... (이전 내용과 동일)" }
    user_request = f"Brand Name: '{brand_name}', Style: '{style_detail}'"
    try:
        response = client.chat.completions.create(
            model="gpt-4o", messages=[system_msg, {"role": "user", "content": user_request}], temperature=0.7,
        )
        invented_subject = response.choices[0].message.content.strip().replace('"', '')
        print(f"✅ GPT-4o invented subject: '{invented_subject}'")
        return invented_subject
    except Exception as e:
        print(f"❌ GPT-4o subject generation failed: {e}. Falling back to brand name.")
        return brand_name

def _build_final_prompt(
    subject: str,
    brand_name: str,
    logo_style: str,
    style_keywords: str, # 스타일 사전을 '키워드 뭉치'로 받음
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    """최종 키워드 리스트 프롬프트를 조립"""
    
    # 1. 주제 + 스타일 키워드
    prompt_parts = [f"{style_keywords}, of a '{subject}'"]

    # 2. 텍스트 지시
    if logo_style.lower() in ["mixed", "text"]:
        font_instruction = f"in a '{font_style}' font" if font_style else "in a clean modern font"
        prompt_parts.append(f"with text '{brand_name}' below, {font_instruction}")

    # 3. 색상 지시
    if colors:
        colors_str = " and ".join([f"'{c}'" for c in colors])
        prompt_parts.append(f"strict color palette of only {colors_str}")

    # 4. 배경
    background_instruction = "on a solid white background" if background == 'white' else "on a solid black background"
    prompt_parts.append(background_instruction)
    
    final_prompt = ", ".join(prompt_parts)
    print(f"✅ FINAL KEYWORD PROMPT: {final_prompt}")
    return final_prompt

# --- 메인 함수 ---
def generate_prompt_with_gpt(
    brand_name: str, logo_style: str, style_detail: Optional[str],
    core_object: Optional[str], font_style: Optional[str],
    colors: List[str], background: str
) -> str:

    final_style_detail = style_detail if style_detail else "Modern"

    # 1. GPT-4o를 이용해 최적의 '스타일 키워드 뭉치'를 생성
    style_keywords = _get_style_keywords_from_gpt(final_style_detail)
    
    # 2. 핵심 상징물 결정 (기존 로직과 동일)
    if core_object and core_object.strip():
        subject = core_object
    else:
        subject = _get_subject_from_gpt(brand_name, final_style_detail)
        
    # 3. 모든 정보를 조합하여 최종 프롬프트 생성
    return _build_final_prompt(
        subject=subject, brand_name=brand_name, logo_style=logo_style,
        style_keywords=style_keywords, # 생성된 키워드 뭉치 사용
        font_style=font_style, colors=colors, background=background
    )