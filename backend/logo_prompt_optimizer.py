import os
import sys
import traceback
from typing import List
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def compress_scene_with_gpt(user_input: str) -> str:
    """
    사용자의 복잡한 묘사를 로고에 적합한 단일 상징으로 압축합니다.
    이 함수는 사용자의 창의적인 아이디어를 AI가 이해하기 쉬운 핵심 요소로 변환하는 중요한 역할을 합니다.
    """
    try:
        system_prompt = (
            "You are a branding assistant that transforms scene descriptions into symbolic logo elements. "
            "If the input describes an action, event, or situation (e.g. 'a fox jumping over fire'), "
            "convert it into a symbolic concept suitable for a logo (e.g. 'fox and fire icon'). "
            "If already suitable, return it as-is. Output must be a short phrase."
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.2,
            max_tokens=50
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ GPT 상징 압축 실패. 원문 사용: {user_input} ({e})")
        return user_input

def generate_symbol_logo_prompt(core_object: str, colors: List[str]) -> str:
    """
    오직 '심볼 로고' 생성을 위해, DALL-E 3를 '명령'하는 강력한 디자인 키워드 프롬프트를 생성합니다.
    """
    try:
        print("🎨 심볼 로고 전용 '디자인 키워드' 프롬프트 생성 중...")

        # 시스템 프롬프트: AI가 '그래픽 디자이너'처럼 생각하고 '명령어'를 만들도록 지시
        system_prompt = (
            "You are an expert logo design prompt engineer for a vector-style AI. "
            "Your task is to convert a user's core object and color request into a powerful, comma-separated, keyword-driven prompt. "
            "This prompt will be used to generate a single, clean, flat, 2D vector logo icon."
            "\n### Rules:\n"
            "1. Start with 'flat vector logo, 2d graphic icon'.\n"
            "2. Incorporate strong, professional design keywords: 'clean single line weight', 'minimalist', 'professional logo', 'masterpiece'.\n"
            "3. To influence the visual style, add design platform names like 'behance, dribbble'.\n"
            "4. The final output must be a single line of comma-separated English keywords and phrases."
        )

        # 심볼 설명: compress_scene_with_gpt를 거친 핵심 요소를 사용
        symbol_desc = f"an icon of {compress_scene_with_gpt(core_object)}"

        # 색상 설명: 명확하고 단순하게 지시
        color_desc = f"using only solid colors: {', '.join(colors)}" if colors else "using a vibrant 2-tone solid color palette"

        # GPT에 전달할 최종 유저 프롬프트
        user_prompt_for_gpt = f"{symbol_desc}, {color_desc}, for a modern brand."

        # GPT-4o 호출하여 최종 프롬프트 생성
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_for_gpt}
            ],
            temperature=0.4,
            max_tokens=250
        )

        final_prompt = response.choices[0].message.content.strip()

        # 최종 프롬프트에 배경 및 네거티브 키워드를 추가하여 완성
        # 이중으로 안전장치를 마련하여 DALL-E 3의 실수를 최소화합니다.
        final_prompt += ", on a solid white background --no 3d, shadow, gradient, texture, details, text, letters, font, signature, watermark"

        print(f"🧾 최종 DALL-E 프롬프트:\n{final_prompt}\n")
        return final_prompt

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ GPT 프롬프트 생성 실패:\n{tb}")
        sys.stderr.write(tb + "\n")
        raise RuntimeError("DALL-E 프롬프트 생성 실패")