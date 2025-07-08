import os
from typing import List, Optional
from openai import OpenAI
import traceback
import sys

# --- OpenAI 클라이언트 초기화 ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- 스타일 키워드 (Playful 기반) ---
STYLE_KEYWORDS: str = (
    "playful but professional logo design, simple modern icon, brand identity, vector illustration, "
    "friendly and approachable, vibrant colors, rounded shapes, 2D, flat, clean design, "
    "no 3d, no photo, no realistic, no shadows, no gradients, no cute characters"
)

# --- GPT로 브랜드 이름 기반 심볼 추론 ---
def call_gpt_for_symbol(brand_name: str) -> str:
    try:
        print(f"🔍 GPT를 통한 '{brand_name}' 브랜드 심볼 추론 중...")

        system_prompt = (
            "You are a logo branding expert. Given a brand name, suggest a single clear object or metaphor "
            "that could represent it visually in a logo. The output should be simple and iconic, such as: "
            "'a blue fox', 'a puzzle piece', 'a rocket', 'a maple leaf', etc. Avoid abstract concepts, "
            "avoid full scenes, and never include text in the suggestion."
        )

        user_prompt = f"Suggest a clear visual metaphor or symbolic object for the brand name '{brand_name}'."

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=30
        )

        result = response.choices[0].message.content.strip().strip("'\"")
        print(f"✅ GPT 추론 결과: {result}")
        return result

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ GPT 호출 실패:\n", tb)
        sys.stderr.write(tb + "\n")
        raise RuntimeError("GPT를 통한 심볼 추론 실패")

# --- core_object를 로고에 적합한 간단한 상징으로 축약 ---
def simplify_object_with_gpt(raw_description: str) -> str:
    try:
        print(f"✂️ 복잡한 상징 '{raw_description}'을 간단화 중...")

        system_prompt = (
            "You are a logo branding assistant. Simplify the following complex or verbose description into a concise object "
            "or metaphor that can be used as a clean and iconic logo symbol. The output must be a short noun phrase like: "
            "'a banana with a soccer ball', 'a rising sun', 'a running fox'. Avoid scenes, actions, or full sentences."
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Simplify this into a single logo symbol: {raw_description}"}
            ],
            temperature=0.3,
            max_tokens=30
        )

        simplified = response.choices[0].message.content.strip().strip("'\"")
        print(f"✅ 단순화 결과: {simplified}")
        return simplified

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ simplify_object_with_gpt 실패:\n", tb)
        sys.stderr.write(tb + "\n")
        return raw_description  # fallback

# --- 최종 프롬프트 생성 함수 ---
def generate_prompt_with_gpt(
    brand_name: str,
    logo_style: str,
    style_detail: Optional[str],
    core_object: Optional[str],
    font_style: Optional[str],
    colors: List[str],
    background: str
) -> str:
    print("⚙️ 프롬프트 생성 시작")

    # 1. 심볼(주제) 결정
    if core_object and core_object.strip():
        subject = simplify_object_with_gpt(core_object.strip())
    else:
        subject = call_gpt_for_symbol(brand_name)

    # 2. 스타일 키워드 고정
    prompt_parts = [f"{STYLE_KEYWORDS}, of a {subject}"]

    # 3. 텍스트 포함 여부
    if logo_style.lower() in ["mixed", "text"]:
        font_instruction = f"in a '{font_style}' font" if font_style else "in a clean, fun font"
        prompt_parts.append(f"with the text '{brand_name}' clearly written, {font_instruction}")

    # 4. 색상 지정
    if colors:
        colors_str = " and ".join([f"'{c}'" for c in colors])
        prompt_parts.append(f"strict color palette of only {colors_str}")

    # 5. 배경 지정
    prompt_parts.append("on a solid white background")

    # 6. 프롬프트 최종 조합
    final_prompt = ", ".join(prompt_parts)
    print(f"🧾 최종 생성 프롬프트:\n{final_prompt}\n")

    return final_prompt