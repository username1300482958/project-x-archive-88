import os
import re
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

# ✨ 스타일 사전을 더 명확하고 강력한 지시어로 수정
STYLE_DICTIONARY: Dict[str, str] = {
    "Minimalist": "ultra-minimalist style, simple clean thin lines, 2D vector, flat icon, high-contrast, using negative space.",
    "Modern": "modern and sleek style, clean lines, uncluttered, professional aesthetic.",
    "Playful": "playful and whimsical cartoon style, rounded corners, fun and friendly, vibrant, energetic mood.",
}

def generate_prompt_with_gpt(
    brand_name: str,
    logo_style: str,
    style_detail: Optional[str],
    core_object: Optional[str],
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    
    print(f"✅ Style: '{style_detail}', Mode: GPT-4o Prompt Generation")
    
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors) if colors else "not specified"
    style_key = style_detail.capitalize() if style_detail else "Modern"
    style_instruction = STYLE_DICTIONARY.get(style_key, STYLE_DICTIONARY["Modern"])

    background_instruction = f"on a solid {background} background"
    if background.lower() == 'white':
        background_instruction = "on a solid pure white background, #FFFFFF"
    elif background.lower() == 'black':
        background_instruction = "on a solid pure black background, #000000"

    # ✨ 최종 전략: 시스템 메시지를 훨씬 더 강력하고 직접적인 '명령'으로 변경
    system_msg = {
        "role": "system",
        "content": """
You are a highly logical and direct DALL-E prompt generator. Your only job is to create a structured, unambiguous prompt. Do not be conversational or creative in your output format.

**Your Task:**
Create a single-line DALL-E prompt by assembling these components in this exact order:
1.  **Subject:** The main visual element.
2.  **Text (if any):** The brand name to be rendered.
3.  **Style:** The visual style and color instructions.
4.  **Composition:** How all elements are arranged.

**Rules:**
-   **Subject First:** The prompt MUST start with "A 2D vector logo of [Subject]...".
-   **Text is Priority:** For 'Mixed' or 'Text' logos, the accurate rendering of the 'Brand Name' is the MOST IMPORTANT task. The prompt must explicitly state this.
-   **Infer from Brand Name:** If the user does not provide a 'Core Object', you MUST analyze the 'Brand Name' (e.g., 'MEGACOFFEE') to infer a relevant subject (e.g., 'a coffee bean'). Do NOT use generic terms like 'abstract shape' unless the brand name itself is abstract.
-   **Be Literal:** Follow the user's brief exactly. Do not add your own creative concepts unless explicitly asked to.
-   Your final output must be a single line of text only.
"""
    }

    # ✨ 최종 수정: GPT-4o에 보낼 사용자 요청을 '레시피' 형식으로 재구성
    
    # 1. 주제(Subject) 결정
    if core_object and core_object.strip():
        # 사용자가 핵심 상징물을 입력한 경우
        subject = core_object
        print(f"✅ Core Object provided by user: '{subject}'")
    else:
        # 사용자가 입력하지 않은 경우, 브랜드 이름에서 유추하도록 지시
        subject = f"a symbol inferred from the brand name '{brand_name}'"
        print(f"🟡 No Core Object. Instructing AI to infer from brand name: '{brand_name}'")

    # 2. 프롬프트 구성 요소 조립
    prompt_components = [
        f"A 2D vector logo of {subject}."
    ]

    # 3. 텍스트 렌더링 지시 추가
    if logo_style.lower() in ["mixed", "text"]:
        font_instruction = f"in a {font_style} font style" if font_style else "in a clean, modern font"
        prompt_components.append(
            f"Crucially, the logo MUST feature the text '{brand_name}' rendered clearly and accurately, {font_instruction}."
        )

    # 4. 스타일 및 색상 지시 추가
    color_instruction = f"The color palette must strictly be {colors_str}." if colors else "The logo should be in a simple black and white color scheme."
    prompt_components.append(f"Style: {style_instruction}. {color_instruction}")

    # 5. 배경 및 최종 지시 추가
    prompt_components.append(f"The entire logo is {background_instruction}.")
    if logo_style.lower() == "symbol":
        prompt_components.append("Absolutely NO text, letters, or words in the image.")
    
    # 최종 프롬프트 조합
    final_prompt = " ".join(prompt_components)
    
    print(f"✅ 최종 생성된 프롬프트: {final_prompt}")
    return final_prompt