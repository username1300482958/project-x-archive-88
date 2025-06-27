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

def generate_prompt_with_gpt(
    brand_name: str,
    logo_style: str,
    style_detail: Optional[str],
    core_object: Optional[str],
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    
    # 이 변수는 'Minimalist'가 아닌 스타일에서만 사용됩니다.
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors)
    
    # 'Minimalist' 스타일은 별도의 단순하고 강력한 로직으로 처리합니다.
    if style_detail and style_detail.capitalize() == "Minimalist":
        print("✅ 'Minimalist' 스타일 감지. 단순 프롬프트 생성 로직을 사용합니다.")
        
        # 1. 핵심 오브젝트 키워드를 정의합니다.
        core_keyword = core_object if core_object else f"abstract shape for {brand_name}"
        
        # 2. 색상 지시어를 더욱 명확하게 만듭니다.
        #    'Minimalist'에서는 첫 번째 색상만 사용하는 것을 강제합니다.
        color_instruction = f"using only the color {colors[0]}" if colors else "monochromatic"

        # 3. 최종 프롬프트를 조합합니다. (불필요한 코드 제거 및 색상 지시어 강화)
        final_prompt = (
            f"ultra-minimalist 2d vector logo, a simple {core_keyword} icon, "
            f"{color_instruction}, 2d flat vector, clean bold lines, centered, "
            f"on a solid {background} background "
            f"--no text, letters, words, realistic, photo, 3d, gradients, shadow, multiple colors, complex details"
        )
        
        print(f"✅ 생성된 단순 프롬프트: {final_prompt}")
        return final_prompt

    # 'Minimalist'가 아닌 다른 스타일은 기존의 GPT-4 호출 방식을 유지합니다.
    print(f"✅ '{style_detail}' 스타일 감지. GPT-4 프롬프트 생성 로직을 사용합니다.")
    
    style_key = style_detail.capitalize() if style_detail else ""
    style_description = ""
    if style_key in STYLE_DICTIONARY:
        style_description = f"The required visual style is '{style_key}', which should be interpreted as: {STYLE_DICTIONARY[style_key]}."

    background_instruction = f"solid {background} background"
    if background.lower() == 'white':
        background_instruction = "a solid pure white background (#FFFFFF)"
    elif background.lower() == 'black':
        background_instruction = "a solid pure black background (#000000)"

    # (이하 GPT-4 호출 로직은 기존과 동일합니다)
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
            model="gpt-4o",
            messages=[system_msg, {"role": "user", "content": user_request}],
            temperature=0.4,
        )
        final_prompt = response.choices[0].message.content.strip()
        
        if logo_style.lower() == "symbol":
            final_prompt += " --no text, letters, words, fonts"
            
        print(f"✅ GPT-4가 생성한 최종 프롬프트: {final_prompt}")
        return final_prompt
    except Exception as e:
        print(f"❌ GPT-4 프롬프트 생성 중 오류 발생: {e}")
        return f"2D vector logo for '{brand_name}', {style_detail} style, on a {background} background."