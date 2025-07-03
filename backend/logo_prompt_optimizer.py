import os
from typing import List, Dict, Optional

# 스타일 사전을 간결한 키워드 묶음으로 정의
STYLE_DICTIONARY: Dict[str, str] = {
    "Minimalist": "minimalist, simple, clean, flat icon",
    "Modern": "modern, sleek, professional, clean lines",
    "Playful": "playful, whimsical, fun, friendly, cartoon",
}

def generate_direct_prompt(
    brand_name: str,
    logo_style: str,
    style_detail: Optional[str],
    core_object: Optional[str],
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    
    print("✅ FINAL VERSION: Keyword-based Direct Prompt Generation ACTIVATED")

    # 1. 주제(Subject) 결정
    if core_object and core_object.strip():
        subject = core_object
    else:
        # 브랜드 이름에서 커피 관련 키워드가 있는지 마지막으로 확인
        if "coffee" in brand_name.lower() or "cafe" in brand_name.lower():
            subject = "a coffee bean symbol"
        else:
            # 그 외에는 브랜드 이름 자체를 상징물로 간주
            subject = f"a symbol for {brand_name}"

    # 2. 프롬프트 키워드 리스트 생성
    prompt_parts = ["2D vector logo"] # 모든 프롬프트의 시작
    prompt_parts.append(subject)

    # 3. 텍스트 키워드 추가
    if logo_style.lower() in ["mixed", "text"]:
        font_instruction = f"'{font_style}' font" if font_style else "modern clean font"
        prompt_parts.append(f"text '{brand_name}'")
        prompt_parts.append(font_instruction)

    # 4. 스타일 키워드 추가
    style_key = style_detail.capitalize() if style_detail else "Modern"
    prompt_parts.append(STYLE_DICTIONARY.get(style_key, STYLE_DICTIONARY["Modern"]))
    
    # 5. 색상 키워드 추가
    if colors:
        colors_str = " ".join([f"'{c}'" for c in colors])
        prompt_parts.append(f"color palette {colors_str}")

    # 6. 배경 및 금지어(Negative Prompt) 키워드 추가
    prompt_parts.append("on a solid white background")
    prompt_parts.append("simple, clean design")
    # 아래는 DALL-E가 엉뚱한 짓을 못하게 막는 금지어들입니다.
    prompt_parts.append("no realistic photo, no 3d render, no gradients, no shadows, no mockup, no poster, no complex background, no extra text")

    # 최종 프롬프트 조합
    final_prompt = ", ".join(prompt_parts)
    print(f"✅ FINAL KEYWORD PROMPT: {final_prompt}")
    return final_prompt