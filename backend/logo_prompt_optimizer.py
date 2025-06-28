import os
import re
from typing import List, Dict, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

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
    [최종 재설계 버전]
    '키워드 레시피' 방식으로 프롬프트를 생성하여 일관된 고품질 로고를 만듭니다.
    1. 사용자의 아이디어(core_object)를 안정적으로 번역/단순화합니다.
    2. 번역된 컨셉과 요구사항을 키워드 형태로 조합하여 최종 프롬프트를 생성합니다.
    """
    
    # 1. 핵심 오브젝트(아이디어) 처리
    final_core_object = core_object if core_object else f"abstract symbol for '{brand_name}'"
    
    # 한글 등 비-알파벳 문자가 있을 경우, 번역 및 단순화 실행
    if core_object and re.search('[^a-zA-Z\s-]', core_object):
        print(f"✅ 한글 또는 특수문자 오브젝트 감지: '{core_object}'. 영어로 번역 및 컨셉 단순화를 시도합니다.")
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a translator and a concept artist. Your job is to translate a user's idea (in any language) into a simple, concise, 2-3 word English phrase suitable for a minimalist logo prompt. For example, if the input is '원자 궤도 안에 있는 간단한 뇌형상', you should output 'atomic brain' or 'brain in an atom'. If the input is '달리는 치타', output 'running cheetah'."},
                    {"role": "user", "content": core_object}
                ],
                temperature=0.1, max_tokens=20
            )
            translated_object = response.choices[0].message.content.strip().lower().replace("'", "")
            print(f"✅ 번역 및 단순화 완료: '{translated_object}'")
            final_core_object = translated_object
        except Exception as e:
            print(f"❌ 핵심 오브젝트 번역 중 오류 발생: {e}. 기본 컨셉을 사용합니다.")
            final_core_object = f"abstract symbol for '{brand_name}'"

    # 2. '키워드 레시피'의 각 재료를 준비합니다.
    prompt_parts = [
        f"logo of a '{final_core_object}'", # 핵심 주제
        f"{style_detail} style",             # 스타일 (Minimalist, Modern 등)
        "vector logo",                      # 로고 형식
        "2d",                               # 차원
        "flat design",                      # 디자인 형식
        "simple icon",                      # 아이콘 스타일
        "clean lines",                      # 선 스타일
        "centered"                          # 구도
    ]

    # 3. 색상 재료 추가 ( '#'을 포함하여 명확하게 지시)
    if colors:
        prompt_parts.append(f"single color: #{colors[0].lstrip('#')}")
    else:
        prompt_parts.append("monochromatic")

    # 4. 배경 재료 추가
    if background and background.lower() == 'black':
        prompt_parts.append("on a solid black background")
    else:
        prompt_parts.append("on a solid white background")

    # 5. 모든 재료를 쉼표로 연결하여 레시피를 완성합니다.
    final_prompt = ", ".join(prompt_parts)

    # 6. 강력한 네거티브 프롬프트로 원치 않는 요소들을 차단합니다.
    final_prompt += " --no realistic photo, 3d, shadow, gradients, textures, intricate details, text, letters, watermark"
    
    print(f"✅ 최종 생성된 프롬프트 (키워드 레시피 방식): {final_prompt}")
    return final_prompt