import os
from typing import List, Dict, Optional

# --- 스타일 키워드 사전 ---
# 'Playful' 스타일만 남기고, 더 강력한 키워드로 고정합니다.
STYLE_KEYWORDS: str = (
    "playful logo design, simple cute cartoon character, vector illustration, "
    "friendly and approachable, vibrant colors, rounded corners, 2D, flat, "
    "no 3d, no photo, no realistic, no shadows, no gradients"
)

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

    print("✅ Direct Prompt Generation Mode (No GPT-4o call)")

    # 1. 주제(Subject) 결정
    if core_object and core_object.strip():
        # 사용자가 핵심 상징물을 입력하면, 그것을 주제로 사용
        subject = core_object
    else:
        # 입력하지 않으면, 브랜드 이름 자체를 주제로 사용
        subject = brand_name

    # 2. 프롬프트 키워드 리스트 생성
    # 'Playful' 스타일 키워드를 고정적으로 사용합니다.
    prompt_parts = [f"{STYLE_KEYWORDS}, of a '{subject}'"]

    # 3. 텍스트 지시 추가
    if logo_style.lower() in ["mixed", "text"]:
        font_instruction = f"in a '{font_style}' font" if font_style else "in a clean, fun font"
        prompt_parts.append(f"with the text '{brand_name}' clearly written, {font_instruction}")

    # 4. 색상 지시 추가
    if colors:
        colors_str = " and ".join([f"'{c}'" for c in colors])
        prompt_parts.append(f"strict color palette of only {colors_str}")

    # 5. 배경 지시 추가
    background_instruction = "on a solid white background"
    prompt_parts.append(background_instruction)
    
    # 최종 프롬프트 조합
    final_prompt = ", ".join(prompt_parts)
    print(f"✅ FINAL KEYWORD PROMPT: {final_prompt}")
    return final_prompt