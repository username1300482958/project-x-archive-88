import os
import re
from typing import List, Dict, Optional

# 스타일 사전을 간결한 키워드 묶음으로 변경
STYLE_DICTIONARY: Dict[str, str] = {
    "Minimalist": "minimalist logo, simple, clean, single icon, negative space",
    "Modern": "modern logo, sleek, clean lines, uncluttered, professional",
    "Playful": "playful logo, fun, friendly, whimsical, rounded corners",
}

# ✨ 최종 버전: GPT-4o를 사용하지 않고 직접 프롬프트를 조합하는 함수
def generate_direct_prompt(
    brand_name: str,
    logo_style: str,
    style_detail: Optional[str],
    core_object: Optional[str],
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    
    print("✅ Direct Prompt Generation Mode ACTIVATED")

    # 1. 주제(Subject) 결정: 브랜드 이름 분석 포함
    if core_object and core_object.strip():
        subject = core_object
    else:
        # 브랜드 이름에서 커피 관련 키워드 유추
        if "coffee" in brand_name.lower() or "cafe" in brand_name.lower():
            subject = "a coffee bean or coffee cup"
        else:
            subject = "an abstract symbol"
    
    prompt_parts = [f"2D vector logo of {subject}"]

    # 2. 텍스트 지시 추가
    if logo_style.lower() in ["mixed", "text"]:
        font_instruction = f"in a {font_style} font" if font_style else "in a clean modern font"
        prompt_parts.append(f"with the text '{brand_name}' written below, {font_instruction}")

    # 3. 스타일 키워드 추가
    style_key = style_detail.capitalize() if style_detail else "Modern"
    style_instruction = STYLE_DICTIONARY.get(style_key, STYLE_DICTIONARY["Modern"])
    prompt_parts.append(style_instruction)

    # 4. 색상 키워드 추가
    if colors:
        colors_str = " and ".join([f"#{c.lstrip('#')}" for c in colors])
        prompt_parts.append(f"using a strict color palette of only {colors_str}")

    # 5. 배경 및 '금지어(Negative Prompt)' 추가 (매우 중요)
    prompt_parts.append("on a solid pure white background")
    prompt_parts.append("NO 3d render, NO photorealistic, NO shadow, NO gradients, NO poster, NO mockup, simple, flat")
    
    final_prompt = ", ".join(prompt_parts)
    print(f"✅ 최종 생성된 직접 프롬프트: {final_prompt}")
    return final_prompt