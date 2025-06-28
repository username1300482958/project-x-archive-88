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
    [최종 해결책]
    추상적인 컨셉을 구체적인 시각적 지침으로 변환하여 고품질 로고를 생성합니다.
    """
    
    # 1. 핵심 오브젝트(아이디어)를 '시각적으로 단순한' 영어 표현으로 변환합니다.
    final_core_object = core_object if core_object else f"abstract geometric shapes for '{brand_name}'"
    
    # 한글 등 비-알파벳 문자가 있을 경우, 번역 및 '시각적' 단순화 실행
    if core_object and re.search('[^a-zA-Z\s-]', core_object):
        print(f"✅ 한글 또는 특수문자 오브젝트 감지: '{core_object}'. 시각적으로 단순한 영어 표현으로 변환합니다.")
        try:
            # GPT-4에게 번역이 아닌, '시각적 컨셉 재해석'을 명확히 지시합니다.
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a concept artist specializing in minimalist logos. Your job is to reinterpret the user's idea into a visually simple, abstract, and geometric English concept for an icon. Focus on shapes, not complex scenes. For example, for '원자 궤도 안에 있는 간단한 뇌형상' (a simple brain shape inside an atomic orbit), output 'interlocking rings with a central node' or 'geometric core with orbiting paths'. For '달리는 치타' (running cheetah), output 'dynamic sweeping lines' or 'abstract cheetah silhouette'."},
                    {"role": "user", "content": core_object}
                ],
                temperature=0.3, max_tokens=25
            )
            translated_object = response.choices[0].message.content.strip().lower().replace("'", "")
            print(f"✅ 시각적 컨셉 변환 완료: '{translated_object}'")
            final_core_object = translated_object
        except Exception as e:
            print(f"❌ 핵심 오브젝트 변환 중 오류 발생: {e}. 기본 추상 형태로 설정합니다.")
            final_core_object = f"abstract geometric shapes for '{brand_name}'"

    # 2. '키워드 레시피'의 각 재료를 강력한 지시어로 준비합니다.
    #    'logo of' 같은 모호한 표현을 제거하고, 직접적인 형용사와 명사만 사용합니다.
    prompt_parts = [
        "minimalist 2d vector logo",          # 핵심 정체성
        f"icon of {final_core_object}",       # 핵심 주제 (명확하게 '아이콘'임을 명시)
        f"{style_detail.lower()} logo style", # 스타일 (소문자로 일관성 유지)
        "flat icon design",                   # 디자인 형식
        "thick clean lines",                  # 선 스타일 (두껍고 깨끗하게)
        "symmetrical",                        # 대칭성
        "high contrast",                      # 대비
        "no background details",              # 배경 디테일 제거
        "centered on page"                    # 구도
    ]

    # 3. 색상 재료 추가
    if colors:
        # '#'를 확실히 포함시키고, 색상 지시를 더 명확하게 합니다.
        prompt_parts.append(f"single solid color, the color is #{colors[0].lstrip('#')}")
    else:
        prompt_parts.append("monochromatic, solid black")

    # 4. 배경 재료 추가
    if background and background.lower() == 'black':
        prompt_parts.append("on a solid black background")
    else:
        prompt_parts.append("on a solid white background") # 기본값

    # 5. 모든 재료를 쉼표로 연결하여 레시피를 완성합니다.
    final_prompt = ", ".join(prompt_parts)

    # 6. 네거티브 프롬프트를 강화하여 원치 않는 요소를 더욱 강력하게 차단합니다.
    final_prompt += " --no realistic, photo, 3d, shadow, gradients, textures, intricate details, complex, busy, text, letters, words, watermark, shading, perspective"
    
    print(f"✅ 최종 생성된 프롬프트 (구체적 지침 방식): {final_prompt}")
    return final_prompt