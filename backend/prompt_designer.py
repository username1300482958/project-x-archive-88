# prompt_designer.py

import os
import json
from typing import List, Optional
from openai import OpenAI

# --- 환경 변수 로드 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

client = OpenAI(api_key=OPENAI_API_KEY)

def create_design_brief_from_gpt(
    brand_name: str,
    logo_style: str,
    colors: List[str],
    font_style: Optional[str],
    core_object: Optional[str]
) -> dict:
    print(f"✅ Generating Design Brief with User Inputs: brand_name='{brand_name}', style='{logo_style}', colors={colors}, font='{font_style}', object='{core_object}'")

    system_msg = {
        "role": "system",
        "content": """
You are a senior brand designer and an expert SVG coder. Your task is to take a user's brief and create a complete JSON design package. You MUST respond with ONLY a valid JSON object.

The user provides their preferences. You MUST respect them.
- If the user provides 'Desired Colors', your generated `color_palette` MUST be based on those colors.
- If the user provides a 'Core Object', your `symbol_idea` MUST be based on that object.
- If the user provides a 'Font Style', your `font_suggestion` MUST match that style.

The JSON structure must be:
{
  "symbol_idea": "A simple, iconic concept for the symbol, described in English.",
  "font_suggestion": "A font family name that matches the requested font style. e.g., 'Arial, sans-serif' for modern, 'Georgia, serif' for classic.",
  "color_palette": { "primary": "#XXXXXX", "secondary": "#XXXXXX", "text_color": "#XXXXXX" },
  "svg_template": "A complete, 200x200 viewBox SVG code string. Use placeholders '{{BRAND_NAME}}', '{{COLOR_PRIMARY}}', '{{COLOR_SECONDARY}}', '{{COLOR_TEXT}}', and '{{FONT_FAMILY}}'. All editable elements must have unique IDs."
}
"""
    }

    # 사용자의 모든 선택사항을 GPT-4o에 명확히 전달
    user_request_parts = [
        f"Brand Name: '{brand_name}'",
        f"Logo Type: '{logo_style}'"
    ]
    if core_object:
        user_request_parts.append(f"Core Object: '{core_object}'")
    if colors:
        user_request_parts.append(f"Desired Colors: '{', '.join(colors)}'")
    if font_style:
        user_request_parts.append(f"Font Style: '{font_style}'")

    user_request = "Please generate a design brief for a logo based on the following user preferences:\n" + "\n".join(user_request_parts)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[system_msg, {"role": "user", "content": user_request}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        design_brief = json.loads(response.choices[0].message.content)
        print("✅ GPT-4o Design Brief generation successful!")
        return design_brief
    except Exception as e:
        print(f"❌ GPT-4o Design Brief generation failed: {e}")
        return {"error": str(e)}