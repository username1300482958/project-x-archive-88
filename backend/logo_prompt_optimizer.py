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
    
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors)
    
    # 'Minimalist' 스타일은 별도의 단순하고 강력한 로직으로 처리합니다.
    if style_detail and style_detail.capitalize() == "Minimalist":
        print("✅ 'Minimalist' 스타일 감지. 단순 프롬프트 생성 로직을 사용합니다.")
        
        core_keyword = core_object if core_object else f"abstract shape for {brand_name}"
        color_instruction = f"using only the color {colors[0]}" if colors else "monochromatic"

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

    # ▼▼▼▼ [수정 1] GPT-4에 보내는 시스템 메시지에 그림자 금지 규칙을 추가합니다. ▼▼▼▼
    system_msg = {
        "role": "system",
        "content": """
You are a world-class Creative Director at a global branding agency. Your sole job is to take a user's structured request and synthesize it into a masterpiece of a prompt for the DALL-E 3 image generation model.

Your task is a strict, step-by-step process:
1.  **Analyze & Conceptualize:** Deeply analyze all user inputs... (기존 내용과 동일)
2.  **Construct Prompt:** Write a single, highly-detailed, and visually descriptive prompt... (기존 내용과 동일)

**STRICT RULES FOR THE FINAL PROMPT:**
- The prompt MUST be in English and a single paragraph.
- It MUST start with "2D vector logo of...".
- It MUST specify "flat design, clean lines, high contrast".
- The final sentence must always be "The logo must be on a solid, clean background."
- **Crucially, the prompt MUST NOT generate any kind of shadows, drop shadows, or 3d-like shading effects. It must be absolutely flat.**
"""
    }
    # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

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
        
        # ▼▼▼▼ [수정 2] GPT-4가 생성한 프롬프트에 그림자 금지 네거티브 프롬프트를 강제로 추가합니다. ▼▼▼▼
        final_prompt = response.choices[0].message.content.strip()
        
        # 항상 그림자와 3D 효과를 금지하도록 네거티브 프롬프트를 추가합니다.
        negative_prompts = " --no 3d, photo, realistic, shadow, gradients, shading"

        if logo_style.lower() == "symbol":
            negative_prompts += ", text, letters, words, fonts"

        final_prompt += negative_prompts
        # ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

        print(f"✅ GPT-4가 생성한 최종 프롬프트: {final_prompt}")
        return final_prompt
    except Exception as e:
        print(f"❌ GPT-4 프롬프트 생성 중 오류 발생: {e}")
        return f"2D vector logo for '{brand_name}', {style_detail} style, on a {background} background."