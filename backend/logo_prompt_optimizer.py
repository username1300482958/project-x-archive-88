import os
import sys
import traceback
from typing import List
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def compress_scene_with_gpt(user_input: str) -> str:
    """
    사용자의 추상적인 아이디어를 AI 아티스트가 이해할 수 있는
    구체적인 '시각적 설계도'로 변환하는 '크리에이티브 디렉터' 역할을 합니다.
    """
    try:
        # --- 최종 핵심 수정: 함수의 역할을 '창의적인 설계자'로 완전히 변경 ---
        system_prompt = (
            "You are a brilliant logo design consultant. Your critical task is to take a user's abstract concept "
            "(e.g., 'atomic brain fusion') and translate it into a simple, concrete, visual description for an AI artist. "
            "Do not just repeat the words. Describe HOW the elements should be combined."
            "\n### Core Logic:\n"
            "1.  **Deconstruct:** Identify the two primary visual objects (e.g., 'atom symbol', 'brain outline').\n"
            "2.  **Synthesize & Instruct:** Describe a clever and simple way to integrate them into a SINGLE, UNIFIED mark. Focus on replacing or merging parts.\n"
            "\n### Examples:\n"
            "* User Input: `atomic brain fusion` -> Your Output: `A simple brain outline serving as the nucleus inside a classic atom symbol`\n"
            "* User Input: `tech leaf` -> Your Output: `A leaf with circuit board lines integrated into its veins`\n"
            "* User Input: `sound wave mountain` -> Your Output: `A mountain range whose peaks form the shape of a classic sound wave`\n"
            "\nOutput must be a short, single-line descriptive phrase in English."
        )
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.2, # 창의적이지만 일관된 지시를 위해 온도 조절
            max_tokens=100
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ GPT 설계도 생성 실패. 원문 사용: {user_input} ({e})")
        return user_input

def generate_symbol_logo_prompt(core_object: str, colors: List[str]) -> str:
    """
    구체적인 '설계도'를 바탕으로, DALL-E가 2D 플랫 로고를 생성하도록 최종 프롬프트를 조립합니다.
    """
    try:
        print("🎨 로고 설계도를 바탕으로 최종 프롬프트 생성 중...")

        # '크리에이티브 디렉터' AI가 생성한 구체적인 설계도를 가져옵니다.
        visual_blueprint = compress_scene_with_gpt(core_object)
        print(f"✅ 생성된 설계도: {visual_blueprint}")

        # DALL-E에게 전달할 최종 프롬프트. 이제 주제(subject)가 매우 명확하고 구체적입니다.
        # 스타일 지시는 이제 거들 뿐입니다.
        style_keywords = "ultra flat 2D vector logo, minimalist logomark, clean bold lines, solid single color"
        color_desc = f"in the color {colors[0]}" if colors else "in a single solid color"
        negative_keywords = "--no shading, shadow, 3d, photo, gradient, texture, details, realism"
        
        final_prompt = f"{style_keywords}, of {visual_blueprint}, {color_desc}, isolated on a plain white background {negative_keywords}"

        print(f"🧾 최종 DALL-E 프롬프트:\n{final_prompt}\n")
        return final_prompt

    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ GPT 프롬프트 생성 실패:\n{tb}")
        sys.stderr.write(tb + "\n")
        raise RuntimeError("DALL-E 프롬프트 생성 실패")