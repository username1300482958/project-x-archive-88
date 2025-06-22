import os
import requests
from typing import List, Dict
from openai import OpenAI

# --- 환경 변수 로드 ---
# DALL-E 3를 사용하므로 OPENAI_API_KEY만 필요합니다.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)


# ✅ [NEW] 스타일 사전을 도입하여, 단순한 키워드를 풍부한 설명으로 변환합니다.
STYLE_DICTIONARY: Dict[str, str] = {
    "minimalist": "ultra-clean lines, essential elements only, generous negative space, simple geometric forms, clarity, precision",
    "modern": "sleek lines, bold typography, abstract shapes, functional, uncluttered, forward-thinking aesthetic",
    "vintage": "retro typography, distressed textures, classic emblem shapes, nostalgic color palettes, hand-drawn feel",
    "geometric": "perfect circles, straight lines, precise angles, symmetry, pattern-based, abstract and logical structure",
    "organic": "curved and flowing lines, nature-inspired shapes (leaves, waves), hand-drawn quality, gentle and harmonious",
    "luxury": "elegant serif fonts or clean sans-serif, metallic accents (gold, silver), sophisticated monograms, minimalist but opulent feel",
}


def generate_prompt_with_gpt(
    brand_name: str,
    logo_style: str, # 'minimalist', 'modern' 등 스타일 사전의 키
    font_style: str = "suitable for the style",
    colors: List[str] = None,
    style_detail: str = None, # 사용자의 추가적인 스타일 요구사항
    background: str = "white"
) -> str:
    """
    GPT-4를 '크리에이티브 디렉터'로 사용하여 DALL-E 3를 위한 최상의 프롬프트를 생성합니다.
    """
    if not colors:
        colors = ["#000000"]
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors)

    # 스타일 사전에서 해당 스타일의 구체적인 설명을 가져옵니다.
    style_description = STYLE_DICTIONARY.get(logo_style.lower(), f"A style that is {logo_style}")
    if style_detail:
        style_description += f", and also {style_detail}"

    # ✅ [NEW] GPT-4에게 내리는 시스템 메시지를 대폭 강화했습니다.
    system_msg = {
        "role": "system",
        "content": """
You are an world-class Creative Director at a global branding agency. Your sole job is to take a user's request and transform it into a masterpiece of a prompt for the DALL-E 3 image generation model.

You must follow this strict process:
1.  **Analyze Brand Name:** First, analyze the provided brand name. Deconstruct its meaning, feeling, and potential visual metaphors. Is it abstract or concrete?
2.  **Conceptualize:** Based on the analysis and the requested style, brainstorm a single, powerful, and commercially viable visual concept for the logo. For an abstract name like "Greenship", you might conceptualize "A minimalist ship where the hull is a single, elegant green leaf".
3.  **Construct Prompt:** Write a single, highly-detailed, and visually descriptive prompt based on your chosen concept. This prompt is for DALL-E 3, which understands complex sentences perfectly.

**STRICT RULES FOR THE PROMPT:**
- The final output MUST be ONLY the prompt string itself. No explanations, no preambles.
- The prompt MUST be in English.
- The prompt MUST start with "A 2D vector logo of...".
- The prompt MUST specify "flat design, clean lines, high contrast".
- The prompt MUST end with the following, exactly as written: " --no text, letters, words, fonts, signature, 3d, photo, realistic, shadow". This is a critical instruction to prevent unwanted elements.
"""
    }

    # 사용자 요청을 GPT-4가 이해하기 쉽게 한 문장으로 정리
    user_request = (
        f"Generate a logo prompt for a brand named '{brand_name}'.\n"
        f"The primary logo style is '{logo_style}', which should be interpreted as: {style_description}.\n"
        f"If the logo includes text, the font style should be '{font_style}'.\n"
        f"The requested colors are: {colors_str}.\n"
        f"The logo background must be a solid {background} background."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o", # 또는 "gpt-4-turbo"
            messages=[
                system_msg,
                {"role": "user", "content": user_request}
            ],
            temperature=0.4, # 일관된 결과물을 위해 온도를 낮춤
        )
        final_prompt = response.choices[0].message.content.strip()
        print(f"✅ GPT-4가 생성한 최종 프롬프트: {final_prompt}")
        return final_prompt
    except Exception as e:
        print(f"❌ GPT-4 프롬프트 생성 중 오류 발생: {e}")
        # 오류 발생 시를 대비한 기본 프롬프트 반환
        return f"A 2D vector logo for '{brand_name}', minimalist style, flat design, on a {background} background. --no text, letters, words"


# ✅ [수정] DALL-E 3 API를 직접 호출하는 함수
def call_dalle3_api(prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
    """
    주어진 프롬프트로 DALL-E 3 이미지를 생성하고 이미지 URL을 반환합니다.
    """
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality=quality,
            n=1,
        )
        image_url = response.data[0].url
        print(f"✅ DALL-E 3 이미지 생성 완료: {image_url}")
        return image_url
    except Exception as e:
        print(f"❌ DALL-E 3 이미지 생성 중 오류 발생: {e}")
        raise  # 오류를 다시 발생시켜 상위 함수에서 처리하도록 함


# ✅ [수정] 최종 로고 생성 엔트리 함수
def generate_logo(
    brand_name: str,
    logo_style: str,
    font_style: str = "modern sans-serif",
    colors: List[str] = None,
    style_detail: str = None,
    background: str = "white"
) -> str:
    # 1. GPT-4로 최상의 프롬프트를 생성
    final_prompt = generate_prompt_with_gpt(
        brand_name=brand_name,
        logo_style=logo_style,
        font_style=font_style,
        colors=colors,
        style_detail=style_detail,
        background=background
    )
    
    # 2. 생성된 프롬프트로 DALL-E 3를 호출하여 이미지 생성
    image_url = call_dalle3_api(final_prompt)
    
    return image_url