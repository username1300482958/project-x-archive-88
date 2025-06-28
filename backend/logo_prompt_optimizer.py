import os
import re
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

# --- [핵심 수정 1] STYLE_DICTIONARY 강화 ---
# 'Minimalist'에 대한 지시사항을 훨씬 더 구체적이고 명확하게 수정합니다.
# 'bold lines'를 'thin lines'로 바꾸고, 텍스트 금지 등 상세 조건을 추가합니다.
STYLE_DICTIONARY: Dict[str, str] = {
    "Minimalist": (
        "ultra-minimalist logo, focusing on a single, simple icon. "
        "Use extremely clean, thin lines (IMPORTANT: not bold or thick). "
        "2D flat vector style. Must use the requested solid colors, with no gradients. "
        "Emphasize negative space and high contrast. "
        "The final image must contain ONLY the icon, with absolutely no text or letters."
    ),
    "Modern": "sleek, abstract shapes, bold typography, functional, uncluttered, forward-thinking aesthetic",
    "Playful": "rounded corners, whimsical characters, bright and vibrant colors, fun and approachable typography, cartoonish elements",
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
    
    # --- [핵심 수정 2] 'Minimalist' 전용 로직 삭제 ---
    # if/else 분기를 제거하여 모든 스타일 요청이 GPT-4o를 통하도록 일원화합니다.
    # 이렇게 하면 GPT-4o가 강화된 STYLE_DICTIONARY를 바탕으로 최적의 프롬프트를 생성합니다.

    print(f"✅ '{style_detail}' 스타일 감지. GPT-4o 프롬프트 생성 로직을 사용합니다.")
    
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors)
    
    style_key = style_detail.capitalize() if style_detail else ""
    style_description = ""
    if style_key in STYLE_DICTIONARY:
        # 강화된 스타일 설명을 GPT-4o에게 전달합니다.
        style_description = f"The required visual style is '{style_key}', which should be interpreted as: {STYLE_DICTIONARY[style_key]}."

    background_instruction = f"solid {background} background"
    if background.lower() == 'white':
        background_instruction = "a solid pure white background (#FFFFFF)"
    elif background.lower() == 'black':
        background_instruction = "a solid pure black background (#000000)"

    # --- 시스템 메시지: 역할 및 규칙 부여 ---
    # (기존 시스템 메시지가 좋다면 그대로 사용하셔도 됩니다. 아래는 예시입니다.)
    system_msg = {
        "role": "system",
        "content": """
You are a world-class Creative Director specializing in DALL-E prompt engineering for logo design.
Your task is to convert user requirements into a single, concise, and effective DALL-E prompt.

**Rules:**
1.  **Be Direct:** Start the prompt immediately with the core subject (e.g., "A minimalist vector logo of a brain..."). Do not use conversational phrases.
2.  **Keyword First:** Place the most important keywords (like style, subject, and color) at the beginning of the prompt.
3.  **Clarity over Complexity:** The prompt must be clear and unambiguous.
4.  **Enforce 'No Text':** If the logo style is 'Symbol', it is CRITICAL that the logo has no text, letters, or words. Explicitly command this.
5.  **Color Adherence:** If colors are specified, they MUST be incorporated as solid colors.
6.  **Style Interpretation:** Use the provided style interpretation from the user prompt as your primary guide.
"""
    }

    # --- 사용자 요청 구성 ---
    prompt_lines = [
        "Generate a logo prompt based on the following requirements:",
        f"- Brand Name: '{brand_name}'",
        f"- Logo Type: '{logo_style}'",
    ]
    if style_description:
        prompt_lines.append(f"- Visual Style: {style_description}")
    if core_object:
        prompt_lines.append(f"- Core Object Suggestion: '{core_object}'")
    if font_style and logo_style.lower() != 'symbol':
        prompt_lines.append(f"- Font Style: '{font_style}'")
    if colors:
        prompt_lines.append(f"- Requested Colors: {colors_str}")
    if background_instruction:
        prompt_lines.append(f"- Background: {background_instruction}")

    user_request = "\n".join(prompt_lines)

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # 또는 gpt-4-turbo
            messages=[system_msg, {"role": "user", "content": user_request}],
            temperature=0.4,
        )
        final_prompt = response.choices[0].message.content.strip()
        
        # --- [핵심 수정 3] 강력한 네거티브 프롬프트 추가 ---
        # Symbol 로고일 경우, 더 강력하고 명시적인 네거티브 프롬프트를 추가합니다.
        if logo_style.lower() == "symbol":
            # DALL-E 3/4에서 --style raw는 프롬프트를 더 충실히 따르도록 돕습니다.
            final_prompt += " --style raw --no text, letters, words, fonts, typography, signature, watermark"
            
        # 프롬프트에 포함될 수 있는 따옴표나 설명 문구 제거
        final_prompt = final_prompt.replace('"', '')
        
        print(f"✅ GPT-4o가 생성한 최종 프롬프트: {final_prompt}")
        return final_prompt
    except Exception as e:
        print(f"❌ GPT-4o 프롬프트 생성 중 오류 발생: {e}")
        # 실패 시에도 기본 프롬프트는 유지
        return f"2D vector logo for '{brand_name}', {style_detail} style, on a {background} background."