import os
import sys
import traceback
import json
from typing import List, Optional, Dict, Any
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_design_brief(
    brand_name: str,
    logo_style: str,
    font_style: Optional[str],
    colors: List[str],
    background: str = "white",
    core_object: Optional[str] = None
) -> Dict[str, Any]:
    try:
        print(f"🎯 디자인 브리프 생성 시작 - 브랜드명: '{brand_name}', 스타일: '{logo_style}'")
        print(f"📌 전달된 core_object: '{core_object}'")

        color_str = ", ".join(colors) if colors else "vibrant colors"
        font_desc = font_style or "modern sans-serif"

        # ✅ 1. core_object가 명시적으로 입력된 경우 GPT 호출 생략
        if core_object and core_object.strip():
            prompt = (
                f"A symbolic logo of {core_object.strip()}, "
                f"using {color_str} on a solid {background} background"
            )
            if logo_style.lower() in ["text", "mixed"]:
                prompt += f" with the text '{brand_name}' in a '{font_desc}' font"

            return {
                "core_object": core_object.strip(),
                "final_prompt": prompt,
                "font_style": font_desc,
                "colors": colors,
                "layout": "icon left, text right",
                "svg_template": None
            }

        # ✅ 2. GPT 호출
        system_prompt = (
            "You are a senior logo designer AI that creates brand identity systems for startups.\n"
            "Given a brand name and style preference, respond ONLY with the following JSON:\n"
            "{\n"
            "  \"core_object\": \"...\",\n"
            "  \"final_prompt\": \"...\",\n"
            "  \"font_style\": \"...\",\n"
            "  \"colors\": [\"#RRGGBB\", ...],\n"
            "  \"layout\": \"...\",\n"
            "  \"svg_template\": \"<svg>...</svg>\" (optional)\n"
            "}\n"
            "Do not include any explanation. Do not include text or logo placeholder words in prompt. Keep it symbolic and minimal."
        )

        user_prompt = (
            f"Brand name: '{brand_name}'\n"
            f"Logo style: '{logo_style}'\n"
            f"Preferred font: '{font_desc}'\n"
            f"Colors: {color_str}\n"
            f"Background: {background}"
        )

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=500,
            response_format="json"
        )

        # ✅ 응답 유효성 검사
        message = response.choices[0].message
        if not message or not message.content:
            raise RuntimeError("❌ GPT 응답이 비어 있음 (message.content 없음)")

        raw = message.content.strip()
        print(f"🧠 GPT 응답 원문:\n{raw}")

        # ✅ JSON 파싱 검증
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"❌ GPT 응답 JSON 파싱 실패:\n{raw}\n\n{e}")

        if not isinstance(result, dict) or "final_prompt" not in result:
            raise RuntimeError("❌ GPT 응답 포맷 오류 또는 필수 필드(final_prompt) 누락")

        return {
            "core_object": result.get("core_object", "").strip(),
            "final_prompt": result.get("final_prompt"),
            "font_style": font_style or result.get("font_style"),
            "colors": colors if colors else result.get("colors", []),
            "layout": result.get("layout"),
            "svg_template": result.get("svg_template"),
        }

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ 디자인 브리프 생성 실패:\n", tb)
        sys.stderr.write(tb + "\n")
        raise RuntimeError("generate_design_brief() 실패")