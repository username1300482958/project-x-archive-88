import os
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)


# ✅ 프론트엔드의 옵션과 키를 정확히 일치시킨 스타일 사전
STYLE_DICTIONARY: Dict[str, str] = {
    # ▼▼▼ "Minimalist"의 내용을 아래와 같이 수정합니다. ▼▼▼
    "Minimalist": "ultra-minimalist, simple icon, 2d, flat, vector, clean lines, solid color, high contrast, negative space",
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

    "Modern": "sleek, abstract shapes, bold typography, functional, uncluttered, forward-thinking aesthetic",
    "Playful": "rounded corners, whimsical characters, bright and vibrant colors, fun and approachable typography, cartoonish elements",
}



# ✅ 가독성과 안정성을 극대화한 최종 프롬프트 생성 로직
def generate_prompt_with_gpt(
    brand_name: str,
    logo_style: str,
    style_detail: Optional[str],
    core_object: Optional[str],
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    
    # [핵심 수정] 'Minimalist' 스타일은 별도의 단순한 로직으로 처리합니다.
    if style_detail and style_detail.capitalize() == "Minimalist":
        print("✅ 'Minimalist' 스타일 감지. 단순 프롬프트 생성 로직을 사용합니다.")
        
        # 필수 키워드 조합
        color_keyword = f"in color {colors[0]}" if colors else "monochromatic"
        core_keyword = core_object if core_object else f"abstract shape for {brand_name}"
        
        # 최종 프롬프트 조합
        # 예: "ultra-minimalist 2d vector logo, a simple brain icon, in color #A855F7, clean lines, on a solid white background --no details, text, 3d"
        final_prompt = (
            f"ultra-minimalist 2d vector logo, {core_keyword}, {color_keyword}, "
            f"icon style, clean bold lines, centered, on a solid {background} background "
            f"--no text, letters, words, realistic, photo, 3d, gradients, shadow, details"
        )
        
        print(f"✅ 생성된 단순 프롬프트: {final_prompt}")
        return final_prompt

    # 'Minimalist'가 아닌 다른 스타일은 기존의 GPT-4 호출 방식을 유지합니다.
    print(f"✅ '{style_detail}' 스타일 감지. GPT-4 프롬프트 생성 로직을 사용합니다.")
    
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors)
    
    style_key = style_detail.capitalize() if style_detail else ""
    style_description = ""
    if style_key in STYLE_DICTIONARY:
        style_description = f"The required visual style is '{style_key}', which should be interpreted as: {STYLE_DICTIONARY[style_key]}."

    background_instruction = f"solid {background} background"
    if background.lower() == 'white':
        background_instruction = "a solid pure white background (#FFFFFF)"
    elif background.lower() == 'black':
        background_instruction = "a solid pure black background (#000000)"

    # 시스템 메시지는 이전과 동일하게 강력한 역할을 부여
    system_msg = {
        "role": "system",
        "content": """
You are a world-class Creative Director at a global branding agency. Your sole job is to take a user's structured request and synthesize it into a masterpiece of a prompt for the DALL-E 3 image generation model.

Your task is a strict, step-by-step process:
1.  **Analyze & Conceptualize:** Deeply analyze all user inputs: Brand Name, Logo Type, Visual Style, and especially the Core Object Suggestion. Synthesize these into a single, strong visual concept for the logo. If a 'Core Object' is provided, it MUST be the central theme. If the name is abstract and no object is provided, you must invent a powerful visual metaphor.
2.  **Construct Prompt:** Write a single, highly-detailed, and visually descriptive prompt based on your chosen concept for DALL-E 3.

**STRICT RULES FOR THE FINAL PROMPT:**
- The prompt MUST be in English and a single paragraph.
- It MUST start with "2D vector logo of...".
- It MUST specify "flat design, clean lines, high contrast".
- The final sentence must always be "The logo must be on a solid, clean background. --no 3d, photo, realistic, shadow, gradients."
"""
    }

    # 각 항목이 있는지 확인하고, 있을 때만 프롬프트에 추가하는 명확한 구조
    prompt_lines = [
        "Generate a logo prompt based on the following requirements:",
        f"- Brand Name: '{brand_name}'",
        f"- Logo Type: '{logo_style}'",
    ]
    if style_description:
        prompt_lines.append(f"- Visual Style: {style_description}")
    if core_object:
        prompt_lines.append(f"- Core Object Suggestion: '{core_object}'")
    # 'symbol' 타입이 아닐 때만 폰트 스타일 추가
    if font_style and logo_style.lower() != 'symbol':
        prompt_lines.append(f"- Font Style: '{font_style}'")
    if colors:
        prompt_lines.append(f"- Requested Colors: {colors_str}")
    if background_instruction:
        prompt_lines.append(f"- Background: {background_instruction}")

    user_request = "\n".join(prompt_lines)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_msg, {"role": "user", "content": user_request}],
            temperature=0.4,
        )
        final_prompt = response.choices[0].message.content.strip()

        # 'symbol' 스타일일 때만 텍스트 제거 구문을 강제로 추가
        if logo_style.lower() == "symbol":
            final_prompt += " --no text, letters, words, fonts"
            
        print(f"✅ GPT-4가 생성한 최종 프롬프트: {final_prompt}")
        return final_prompt
    except Exception as e:
        print(f"❌ GPT-4 프롬프트 생성 중 오류 발생: {e}")
        return f"2D vector logo for '{brand_name}', {style_detail} style, on a {background} background."