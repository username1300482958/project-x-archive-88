import os
import re
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ STYLE_DICTIONARY는 이제 GPT-4에 참고자료로만 제공되므로, 단순화하거나 그대로 두어도 좋습니다.
STYLE_DICTIONARY: Dict[str, str] = {
    "Minimalist": "ultra-minimalist, simple icon, 2d, flat, vector, clean lines, solid color, high contrast, negative space",
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
    """
    [최종 완성본] 모든 로고 생성 요청을 하나의 강력한 프로세스로 통합합니다.
    1. 사용자의 아이디어(core_object)가 한글이면 영어로 번역하고 미니멀한 컨셉으로 다듬습니다.
    2. 번역/정제된 컨셉과 다른 요구사항을 조합하여 최종 프롬프트를 생성합니다.
    """
    
    # 1. 핵심 오브젝트(아이디어) 처리
    final_core_object = core_object if core_object else f"abstract symbol for '{brand_name}'"
    
    # 정규식을 사용하여 core_object에 한글 등 비-알파벳 문자가 있는지 확인합니다.
    if core_object and re.search('[^a-zA-Z\s-]', core_object):
        print(f"✅ 한글 또는 특수문자 오브젝트 감지: '{core_object}'. 영어로 번역 및 컨셉 단순화를 시도합니다.")
        try:
            # GPT-4에게 번역 및 단순화 작업을 명확히 지시
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a translator and a concept artist. Your job is to translate a user's idea (in any language) into a simple, concise, 2-3 word English phrase suitable for a minimalist logo prompt. For example, if the input is '원자 궤도 안에 있는 간단한 뇌형상', you should output 'atomic brain' or 'brain in an atom'. If the input is '달리는 치타', output 'running cheetah'."},
                    {"role": "user", "content": core_object}
                ],
                temperature=0.1,
                max_tokens=20
            )
            translated_object = response.choices[0].message.content.strip().lower().replace("'", "")
            print(f"✅ 번역 및 단순화 완료: '{translated_object}'")
            final_core_object = translated_object
        except Exception as e:
            print(f"❌ 핵심 오브젝트 번역 중 오류 발생: {e}. 기본 컨셉을 사용합니다.")
            final_core_object = f"abstract symbol for '{brand_name}'" # 실패 시 안전장치

    # 2. 색상 지시어 처리
    #    DALL-E가 색상 코드를 더 잘 인식하도록 명확한 구문을 사용합니다.
    color_instruction = f"primary color {colors[0]}" if colors else "monochromatic black"

    # 3. 배경 지시어 처리
    background_instruction = "solid pure white background" # 기본값 흰색으로 통일
    if background and background.lower() == 'black':
        background_instruction = "solid pure black background"

    # 4. 최종 프롬프트 조합 (하나의 강력한 템플릿 사용)
    #    모든 스타일 요청을 이 템플릿으로 처리하여 일관된 고품질을 유지합니다.
    final_prompt = (
        f"minimalist 2d vector logo of a '{final_core_object}', "
        f"{style_detail} style, {color_instruction}, "
        f"logo design, simple icon, centered, on a {background_instruction} "
        f"--no realistic, photo, 3d, gradients, shadow, detailed, text, letters"
    )
    
    print(f"✅ 최종 생성된 프롬프트: {final_prompt}")
    return final_prompt