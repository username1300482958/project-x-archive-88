import os
import sys
import traceback
from typing import List
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def compress_scene_with_gpt(user_input: str) -> str:
    """
    사용자의 묘사를 로고에 적합한 간결한 핵심 상징으로 압축합니다.
    """
    try:
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
    오직 '심볼 로고' 생성을 위해, DALL-E 3를 '명령'하는 매우 강력하고 명확한 프롬프트를 생성합니다.
    AI가 3D로 해석할 여지를 완전히 제거하는 것을 최우선 목표로 합니다.
    """
    try:
        print("🎨 심볼 로고 전용 '디자인 키워드' 프롬프트 생성 중...")

        # --- 최종 핵심 수정: 시스템 프롬프트를 더욱 공격적으로 변경 ---
        # 2D 스타일을 최우선으로, 그리고 가장 강력하게 지시합니다.
        system_prompt = (
            "You are an expert prompt engineer for DALL-E, specializing in generating **strictly 2D, ultra-flat vector logos.** "
            "Your primary goal is to create a prompt that is impossible for the AI to interpret as 3D or photographic. "
            "The prompt must force a flat, simple, graphic style, even for concepts strongly associated with 3D renderings (like atoms or spheres)."
            "\n### Prompt Structure Rules:\n"
            "1.  **Crucial Style Prefix:** **ALWAYS** start the prompt with the phrase `ultra flat 2D vector logo,`. This is the most important rule.\n"
            "2.  **Subject Definition:** Follow with the subject, like `of a {core_object}`.\n"
            "3.  **Reinforcing Style Keywords:** Add a barrage of style keywords like `minimalist icon`, `flat design illustration`, `solid bold colors`, `clean bold lines`. Using 'bold' helps prevent thin, pseudo-3D lines.\n"
            "4.  **In-Prompt Negative Constraint:** Explicitly add the phrase `Strictly no 3D rendering, no shadows, no gradients.` directly into the prompt body.\n"
            "5.  **Isolation:** Ensure the logo is `isolated on a plain white background`.\n"
            "6.  **Final Output:** Must be a single, comma-separated line of English keywords."
        )

        compressed_object = compress_scene_with_gpt(core_object)
        color_desc = f"using only the solid colors: {', '.join(colors)}" if colors else "using a vibrant 2-tone solid color palette"
        user_prompt_for_gpt = f"Core Object: `{compressed_object}`, Colors: `{color_desc}`"

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_for_gpt}
            ],
            temperature=0.1, # 매우 엄격한 규칙을 따르도록 온도를 낮게 유지
            max_tokens=250
        )

        final_prompt = response.choices[0].message.content.strip()

        # 최종 안전장치: 네거티브 프롬프트는 계속 유지
        final_prompt += ", --no photo, 3d, shading, shadow, gradient, texture, realism, mock-up, presentation"

        print(f"🧾 최종 DALL-E 프롬프트:\n{final_prompt}\n")
        return final_prompt

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ GPT 프롬프트 생성 실패:\n{tb}")
        sys.stderr.write(tb + "\n")
        raise RuntimeError("DALL-E 프롬프트 생성 실패")