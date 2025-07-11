import os
import sys
import traceback
from typing import List
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def compress_scene_with_gpt(user_input: str) -> str:
    """
    사용자의 복잡한 묘사를 로고에 적합한 핵심 상징으로 압축합니다.
    """
    try:
        # 시스템 프롬프트를 더 명확하게 수정: '핵심 상징 요소'를 강조
        system_prompt = (
            "You are a branding expert. Your task is to distill a user's description "
            "into a concise 2-5 word phrase representing the core symbolic elements for a logo. "
            "Example: 'a fox jumping over fire' becomes 'fox and fire'. "
            "Example: 'a roaring lion wearing a crown' becomes 'crowned lion head'."
            "Output must be a short phrase in English."
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.1,
            max_tokens=50
        )
        return response.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"⚠️ GPT 상징 압축 실패. 원문 사용: {user_input} ({e})")
        return user_input

def generate_symbol_logo_prompt(core_object: str, colors: List[str]) -> str:
    """
    오직 '심볼 로고' 생성을 위해, DALL-E 3를 '명령'하는 강력하고 명확한 프롬프트를 생성합니다.
    포스터나 목업이 아닌, 순수한 로고 아이콘 생성을 목표로 합니다.
    """
    try:
        print("🎨 심볼 로고 전용 '디자인 키워드' 프롬프트 생성 중...")

        # --- 핵심 수정 사항: 시스템 프롬프트를 완전히 재구성 ---
        # 모호한 키워드(dribbble, behance)를 제거하고, '고립된 심볼'임을 명확히 지시합니다.
        system_prompt = (
            "You are an expert prompt engineer for DALL-E, specializing in minimalist vector logos. "
            "Your task is to create a direct, keyword-focused prompt to generate a single, unified, and isolated logo symbol. "
            "The output must NOT be a poster, mock-up, or a scene."
            "\n### Rules:\n"
            "1.  **Subject First:** Start with a clear description, like `A logo of {core_object}` or `A symbol combining {elements}`.\n"
            "2.  **Style Keywords:** Use precise terms like `flat icon`, `vector logo`, `minimalist design`, `clean lines`, `solid colors`.\n"
            "3.  **Composition:** The elements must form a `single unified symbol`.\n"
            "4.  **Background:** Crucially, specify that the logo must be `isolated on a plain white background`. The word 'isolated' is key.\n"
            "5.  **Final Output:** Must be a single line of comma-separated English keywords.\n"
            "\n### What to AVOID:\n"
            "Do NOT use ambiguous style words like `behance`, `dribbble`, `masterpiece`, `professional logo`, `modern brand`. These often lead to unwanted poster or mock-up results."
        )

        # compress_scene_with_gpt를 거친 핵심 요소를 사용
        compressed_object = compress_scene_with_gpt(core_object)

        # 색상 설명
        color_desc = f"using only the solid colors: {', '.join(colors)}" if colors else "using a vibrant 2-tone solid color palette"

        # GPT에 전달할 유저 프롬프트 (더 단순하고 명확하게)
        user_prompt_for_gpt = f"Core Object: `{compressed_object}`, Colors: `{color_desc}`"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_for_gpt}
            ],
            temperature=0.2, # 더 일관된 결과를 위해 온도를 낮춤
            max_tokens=250
        )

        final_prompt = response.choices[0].message.content.strip()

        # DALL-E가 규칙을 어길 경우를 대비한 최종 안전장치
        final_prompt += ", --no photo, 3d, shadow, gradient, texture, details, text, letters, font, signature, watermark, mock-up, presentation"

        print(f"🧾 최종 DALL-E 프롬프트:\n{final_prompt}\n")
        return final_prompt

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ GPT 프롬프트 생성 실패:\n{tb}")
        sys.stderr.write(tb + "\n")
        raise RuntimeError("DALL-E 프롬프트 생성 실패")