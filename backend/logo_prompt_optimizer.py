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
        "an ultra-minimalist vector logo, focusing on a single, simple icon with extremely clean, thin lines. "
        "It should be a 2D flat design that heavily emphasizes negative space and high contrast. "
        "The final image must contain ONLY the specified icon, with absolutely no text or letters."
    ),
    "Modern": (
        "a sleek and modern logo using abstract shapes. The design should feel uncluttered, forward-thinking, and functional. "
        "Think geometric precision combined with smooth curves, embodying a contemporary and professional aesthetic."
    ),
    "Playful": (
        "a fun and whimsical logo with cartoonish elements. It should feature rounded corners, bright and vibrant colors, "
        "and an approachable, friendly character or shape. The overall mood should be cheerful and energetic."
    ),
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
    
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors) if colors else "not specified"
    style_key = style_detail.capitalize() if style_detail else "Modern"
    style_description = STYLE_DICTIONARY.get(style_key, STYLE_DICTIONARY["Modern"])

    background_instruction = f"on a solid {background} background"
    if background.lower() == 'white':
        background_instruction = "on a solid pure white background (#FFFFFF)"
    elif background.lower() == 'black':
        background_instruction = "on a solid pure black background (#000000)"

    system_msg = {
        "role": "system",
        "content": """
You are a world-class DALL-E prompt engineer specializing in logo design. Your role changes based on the user's request.

**Core Rules (Apply to ALL tasks):**
1.  **Enforce Color Palette:** You must weave the desired colors into the description of the core object itself, making them seem essential. Example: "A logo of a phoenix with feathers shimmering in vibrant #F97316 and radiant #FFD700 hues."
2.  **Vector & Clean:** The final output should always be described as a '2D vector logo', 'flat icon', or similar to ensure a clean, usable result.
3.  **Direct Command:** Your entire output must be a single, direct instruction for DALL-E, starting with "A 2D vector logo...". Do not add conversational text or quotation marks.
4.  **Text Handling:** For 'Symbol' type logos, ensure NO text appears. For 'Text' or 'Mixed' types, the provided Brand Name is the MOST important element and must be rendered beautifully.
"""
    }

    # ✨ [조건부 로직] '핵심 상징물' 입력 여부에 따라 AI의 역할과 지시를 변경합니다.
    if core_object and core_object.strip():
        # --- 1. 사용자가 상징물을 입력한 경우: '기술자' 모드 ---
        print("✅ 사용자가 핵심 상징물을 입력했습니다. '기술자' 모드로 작동합니다.")
        temperature = 0.3  # 창의성을 낮추고 지시를 정확히 따르도록 설정
        
        prompt_lines = [
            "Your task is to be a precise 'Technician'. Faithfully translate the user's brief into a high-quality DALL-E prompt. Do not invent new concepts.",
            "--- Creative Brief ---",
            f"- Brand Name: '{brand_name}'",
            f"- Core Object to visualize: '{core_object}'",
            f"- Desired Colors: {colors_str}",
            f"- Visual Style: {style_key} ({style_description})",
            f"- Logo Type: '{logo_style}'",
            f"- Font Style: '{font_style if font_style else 'A font that matches the visual style'}'",
            f"- Background: {background_instruction}",
        ]
        if logo_style.lower() == "symbol":
            prompt_lines.append("- IMPORTANT: This is a SYMBOL-only logo. Absolutely no text should appear.")

    else:
        # --- 2. 사용자가 상징물을 입력하지 않은 경우: '크리에이티브 디렉터' 모드 ---
        print("🟡 사용자가 핵심 상징물을 입력하지 않았습니다. '크리에이티브 디렉터' 모드로 작동합니다.")
        temperature = 0.7  # 창의성을 높여 새로운 아이디어를 제안하도록 설정

        prompt_lines = [
            "Your task is to be a brilliant 'Creative Director'. The user has not provided a core object. Your mission is to INVENT a compelling, symbolic object or concept based on the Brand Name and style. Then, craft a DALL-E prompt for it.",
            "--- Creative Brief ---",
            f"- Brand Name: '{brand_name}'",
            f"- Desired Colors: {colors_str}",
            f"- Visual Style: {style_key} ({style_description})",
            f"- Logo Type: '{logo_style}'",
            f"- Font Style: '{font_style if font_style else 'A font that matches the visual style'}'",
            f"- Background: {background_instruction}",
        ]
        if logo_style.lower() == "symbol":
            prompt_lines.append("- IMPORTANT: This is a SYMBOL-only logo. Invent a concept for the symbol, but ensure absolutely no text appears in the image.")

    user_request = "\n".join(prompt_lines)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_msg, {"role": "user", "content": user_request}],
            temperature=temperature, # ✨ [조건부 로직] 동적으로 조절된 temperature 값 사용
        )
        final_prompt = response.choices[0].message.content.strip()
        final_prompt = re.sub(r'^(Prompt:|Create a logo for:|A logo for|")', '', final_prompt, flags=re.IGNORECASE).strip()
        
        print(f"✅ GPT-4o가 생성한 최종 프롬프트: {final_prompt}")
        return final_prompt
    except Exception as e:
        print(f"❌ GPT-4o 프롬프트 생성 중 오류 발생: {e}")
        color_prompt = f"in colors {colors_str}" if colors and colors_str != "not specified" else ""
        object_prompt = core_object if core_object else brand_name
        return f"2D vector logo for '{object_prompt}', {style_detail} style, {color_prompt}, on a {background_instruction}."