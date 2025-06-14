# logo_prompt_optimizer.py

import os
import requests
from typing import List
from openai import OpenAI

# 환경 변수에서 API 키 읽기
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
IMAGINE_API_KEY = os.getenv("IMAGINE_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ GPT로 로고 생성 프롬프트 생성 (판단 제거, 무조건 생성만 수행)
def generate_prompt_with_gpt(
    brand_name: str,
    logo_style: str,
    font_style: str = "modern sans-serif",
    colors: List[str] = None,
    style_detail: str = None,
    background: str = "white"
) -> str:
    if not colors:
        colors = ["#000000"]
    colors_str = ", ".join(f"#{c.lstrip('#')}" for c in colors)

    background = background.strip().lower()
    if background not in ["black", "white"]:
        background = "white"

    system_msg = {
        "role": "system",
        "content": (
            "You are a professional logo prompt engineer for an AI logo generation system.\n"
            "Your job is to convert a brand name and style into a clear, visually descriptive prompt.\n"
            "All logos must be 2D, flat, and vector-style. Never use placeholder text like 'logo' or 'brand name'."
        )
    }

    user_msg_content = ""

    if logo_style.lower() == "symbol":
        user_msg_content = (
            f'Create a clean and creative symbolic logo that visually represents the brand name "{brand_name}".\n'
            f'- Use color(s): {colors_str}\n'
            f'- Background: {background}\n'
            f'- Style: {style_detail or "minimalist and modern"}\n'
            f'- Do not include text, letters, or UI elements.\n'
            f'- Focus on meaningful visual symbolism in vector style.'
        )

    elif logo_style.lower() == "text":
        user_msg_content = (
            f'Create a clean and modern wordmark logo for the brand "{brand_name}".\n'
            f'- Font style: {font_style}\n'
            f'- Use color(s): {colors_str}\n'
            f'- Background: {background}\n'
            f'- Visual tone: {style_detail or "refined and minimal"}\n'
            f'- No symbols or icons, just typography.'
        )

    elif logo_style.lower() == "mixed":
        user_msg_content = (
            f'Create a hybrid logo combining the brand name "{brand_name}" and a meaningful symbol.\n'
            f'- Font: {font_style}\n'
            f'- Use color(s): {colors_str}\n'
            f'- Background: {background}\n'
            f'- Visual tone: {style_detail or "balanced and modern"}\n'
            f'- The icon should relate to the brand name and be clearly positioned above or beside the text.'
        )

    else:
        raise ValueError(f"Unsupported logo style: {logo_style}")

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            system_msg,
            {"role": "user", "content": user_msg_content.strip()}
        ],
        temperature=0.8
    )
    return response.choices[0].message.content.strip()


# ✅ Imagine API 호출 함수
def call_imagine_api(prompt: str, aspect_ratio: str = "1:1", style: str = "vector") -> str:
    url = "https://api.vyro.ai/v2/image/generate"
    headers = {"Authorization": f"Bearer {IMAGINE_API_KEY}"}
    data = {
        "prompt": prompt,
        "style": style,
        "aspect_ratio": aspect_ratio
    }
    response = requests.post(url, headers=headers, files=data)
    response.raise_for_status()
    return response.json().get("image_url")


# ✅ 최종 로고 생성 엔트리 함수
def generate_logo(
    brand_name: str,
    logo_style: str,
    font_style: str = "modern sans-serif",
    colors: List[str] = None,
    style_detail: str = None,
    background: str = "white"
) -> str:
    prompt = generate_prompt_with_gpt(
        brand_name=brand_name,
        logo_style=logo_style,
        font_style=font_style,
        colors=colors,
        style_detail=style_detail,
        background=background
    )
    image_url = call_imagine_api(prompt)
    return image_url