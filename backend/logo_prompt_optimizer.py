import os
import re
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

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
    
    print(f"✅ '{style_detail}' 스타일 감지. GPT-4o 프롬프트 생성 로직을 사용합니다.")
    
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

    # --- [핵심 수정] GPT-4o에 대한 시스템 메시지를 '창의적 미션' 형태로 변경 ---
    system_msg = {
        "role": "system",
        "content": """
You are a master DALL-E prompt artist, skilled in creating prompts with creative and nuanced language. Your goal is to translate user needs into a prompt that generates a beautiful and accurate logo.

**YOUR #1 MISSION: GUARANTEE COLOR ACCURACY**
DALL-E often ignores color requests. To overcome this, you MUST creatively and grammatically weave the requested color(s) into the description of the 'Core Object' itself. The color must feel like an intrinsic, essential part of the subject, not a tacked-on afterthought.

- **Bad prompt:** "Logo of a lion wearing a crown, in gold." (Color is an afterthought)
- **Good prompt:** "Logo of a lion with a brilliant golden crown." (Color is integrated naturally)
- **Good prompt:** "A minimalist logo of a majestic lion, its crown rendered in solid gold." (Creative integration)

You have the creative freedom to find the most natural and powerful phrasing. This applies to ANY 'Core Object', whether it's a single word ('brain') or a complex phrase ('a phoenix rising from a book').

**Other Rules:**
1.  **Direct & Effective:** The final prompt must be a single, direct command for DALL-E.
2.  **No Text for Symbols:** For 'Symbol' logos, use a strong negative prompt to ensure NO text is generated.
3.  **Respect the Style:** Fully utilize the provided 'Visual Style' description in your final prompt.
"""
    }

    # --- 사용자 요청 구성 ---
    # GPT-4o가 창의력을 발휘할 수 있도록 정보를 명확히 전달합니다.
    prompt_lines = [
        "Please generate a single, powerful DALL-E prompt based on the following creative brief:",
        f"- Core Object to visualize: '{core_object if core_object else 'an abstract shape'}'",
        f"- Desired Colors to integrate: {colors_str if colors else 'Monochromatic / Black & White'}",
        f"- Visual Style to apply: {style_description}",
        f"- Logo Type: '{logo_style}'",
        f"- Background: {background_instruction}",
    ]

    user_request = "\n".join(prompt_lines)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_msg, {"role": "user", "content": user_request}],
            temperature=0.5, # 창의성을 약간 높여 자연스러운 문장 생성을 유도
        )
        final_prompt = response.choices[0].message.content.strip()
        
        if logo_style.lower() == "symbol":
            final_prompt += " --style raw --no text, letters, words, fonts, typography, signature, watermark"
            
        final_prompt = re.sub(r'Prompt:|"', '', final_prompt).strip()
        
        print(f"✅ GPT-4o가 생성한 최종 프롬프트: {final_prompt}")
        return final_prompt
    except Exception as e:
        print(f"❌ GPT-4o 프롬프트 생성 중 오류 발생: {e}")
        return f"2D vector logo for '{brand_name}', {style_detail} style, on a {background} background."