import os
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)


# ✅ [수정] 사용자님의 UI에 맞춰 불필요한 스타일 제거
STYLE_DICTIONARY: Dict[str, str] = {
    "minimalist": "ultra-clean lines, essential elements only, generous negative space, simple forms, clarity",
    "modern": "sleek, abstract shapes, bold typography, functional, uncluttered, forward-thinking aesthetic",
    "playful": "rounded corners, whimsical characters, bright and vibrant colors, fun and approachable typography, cartoonish elements",
}


# ✅ [수정] 프론트엔드 UI 구조에 맞춰 파라미터 및 로직 전체 재설계
def generate_prompt_with_gpt(
    brand_name: str,
    logo_style: str,                  # 'symbol', 'text', 'mixed'
    style_detail: Optional[str],        # 'minimalist', 'modern', 'playful'
    brand_values: Optional[List[str]],  # '친근한', '전문적인' 등
    core_object: Optional[str],         # 사용자가 직접 제안하는 상징물
    layout: Optional[str],              # 혼합형 로고의 레이아웃
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors)
    
    # 각 입력값을 프롬프트에 사용할 문장으로 가공합니다.
    style_desc_str = f"The required visual style is '{style_detail}', which means: {STYLE_DICTIONARY.get(style_detail, style_detail)}." if style_detail else ""
    values_str = f"The core brand values to express are: {', '.join(brand_values)}." if brand_values else ""
    object_str = f"The user suggested a core visual object to build upon: '{core_object}'." if core_object else ""
    
    # logo_style에 따라 상세 지시사항을 다르게 구성
    details_list = []
    if logo_style.lower() == "symbol":
        details_list.append("This is a symbol-only logo. It must NOT contain any text or letters.")
        details_list.append(object_str)
    
    elif logo_style.lower() == "text":
        details_list.append(f"This is a text-only (wordmark) logo. Focus on beautiful typography for the brand name. The requested font style is '{font_style}'.")

    elif logo_style.lower() == "mixed":
        layout_str = f"The layout should be: '{layout}'." if layout else "The symbol and text should be well-balanced."
        details_list.append(f"This is a hybrid logo combining a symbol and the brand name text. The font style for the text should be '{font_style}'. {layout_str}")
        details_list.append(object_str)

    final_details_str = "\n".join(filter(None, details_list))

    # ✅ [수정] 시스템 메시지가 새로운 입력값들을 모두 이해하고 활용하도록 업데이트
    system_msg = {
        "role": "system",
        "content": """
You are an world-class Creative Director at a global branding agency. Your sole job is to take a user's detailed request and transform it into a masterpiece of a prompt for the DALL-E 3 image generation model.

Your task is a strict, step-by-step process:
1.  **Analyze & Conceptualize:** Deeply analyze all user inputs: Brand Name, Primary Style (symbol, text, mixed), Style Details (e.g., minimalist), Brand Values (e.g., friendly, professional), Core Object, and Layout instructions. Synthesize these into a single, strong visual concept. The 'Brand Values' define the mood and concept, while the 'Style Details' define the visual execution. If a 'Core Object' is provided, it MUST be the central theme.
2.  **Construct Prompt:** Write a single, highly-detailed, and visually descriptive prompt based on your chosen concept. This prompt is for DALL-E 3.

**STRICT RULES FOR THE FINAL PROMPT:**
- The final output MUST be ONLY the prompt string itself. No explanations, no preambles.
- The prompt MUST be in English and a single paragraph.
- It MUST start with "2D vector logo of...".
- It MUST specify "flat design, clean lines, high contrast".
- The final sentence of the prompt must always be "The logo must be on a solid, clean background. --no 3d, photo, realistic, shadow, gradients (unless explicitly requested)."
"""
    }

    user_request = (
        f"Generate a logo prompt based on the following detailed requirements:\n"
        f"Brand Name: '{brand_name}'\n"
        f"Logo Type: '{logo_style}'\n"
        f"Visual Style Details: {style_desc_str}\n"
        f"Brand Values/Feeling: {values_str}\n"
        f"User-suggested Core Object: {object_str}\n"
        f"Detailed Instructions: {final_details_str}\n"
        f"Requested Colors: {colors_str}\n"
        f"Background Color: {background}"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_msg, {"role": "user", "content": user_request}],
            temperature=0.4,
        )
        final_prompt = response.choices[0].message.content.strip()

        if logo_style.lower() == "symbol":
            final_prompt += " --no text, letters, words, fonts, signature"
            
        print(f"✅ GPT-4가 생성한 최종 프롬프트: {final_prompt}")
        return final_prompt
    except Exception as e:
        print(f"❌ GPT-4 프롬프트 생성 중 오류 발생: {e}")
        return f"2D vector logo for '{brand_name}', {style_detail} style, on a {background} background."

# DALL-E 3 호출 함수 (변경 없음)
def call_dalle3_api(prompt: str, size: str = "1024x1024", quality: str = "standard") -> str:
    # ... (기존과 동일)
    try:
        response = client.images.generate(
            model="dall-e-3", prompt=prompt, size=size, quality=quality, n=1,
        )
        return response.data[0].url
    except Exception as e:
        print(f"❌ DALL-E 3 이미지 생성 중 오류 발생: {e}")
        raise

# ✅ 엔트리 함수 시그니처를 새로운 파라미터에 맞게 최종 수정
def generate_logo(
    brand_name: str,
    logo_style: str,
    colors: List[str],
    background: str,
    style_detail: Optional[str] = None, # '스타일 세부 선택'
    brand_values: Optional[List[str]] = None, # '브랜드 가치/느낌'
    core_object: Optional[str] = None, # '핵심 상징물'
    layout: Optional[str] = None, # '레이아웃'
    font_style: Optional[str] = None
) -> str:
    final_prompt = generate_prompt_with_gpt(
        brand_name=brand_name,
        logo_style=logo_style,
        style_detail=style_detail,
        brand_values=brand_values,
        core_object=core_object,
        layout=layout,
        font_style=font_style,
        colors=colors,
        background=background
    )
    image_url = call_dalle3_api(final_prompt)
    return image_url