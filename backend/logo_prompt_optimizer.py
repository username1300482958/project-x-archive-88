import os
import sys
import traceback
from typing import List, Dict
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 색상 매핑 데이터베이스
COLOR_MAPPING = {
    # 보라색 계열
    "A855F7": "purple",
    "8B5CF6": "violet", 
    "9333EA": "purple",
    "7C3AED": "purple",
    "6D28D9": "deep purple",
    
    # 파란색 계열
    "3B82F6": "blue",
    "2563EB": "blue",
    "1D4ED8": "dark blue",
    "1E40AF": "navy blue",
    "60A5FA": "light blue",
    
    # 빨간색 계열
    "EF4444": "red",
    "DC2626": "red",
    "B91C1C": "dark red",
    "F87171": "light red",
    
    # 초록색 계열
    "10B981": "green",
    "059669": "green",
    "047857": "dark green",
    "34D399": "light green",
    
    # 주황색 계열
    "F97316": "orange",
    "EA580C": "orange",
    "C2410C": "dark orange",
    "FB923C": "light orange",
    
    # 기타
    "000000": "black",
    "FFFFFF": "white",
    "6B7280": "gray",
    "374151": "dark gray",
}

def hex_to_color_name(hex_code: str) -> str:
    """HEX 코드를 DALL-E가 이해할 수 있는 색상명으로 변환"""
    hex_code = hex_code.upper().replace("#", "")
    return COLOR_MAPPING.get(hex_code, "dark blue")  # 기본값: 어두운 파란색

def compress_scene_with_gpt(user_input: str) -> str:
    """
    사용자의 추상적인 아이디어를 구체적이고 단순한 시각적 설계도로 변환
    """
    try:
        # 더 구체적이고 제한적인 시스템 프롬프트
        system_prompt = (
            "You are a logo design expert. Transform abstract concepts into SIMPLE, CONCRETE visual instructions. "
            "Focus on creating ONE unified symbol by combining or replacing elements.\n\n"
            "Key Rules:\n"
            "- Use simple geometric shapes\n"
            "- Describe element integration clearly\n"
            "- Keep it minimal and recognizable\n"
            "- Use words like 'half', 'partial', 'outline', 'silhouette'\n\n"
            "Examples:\n"
            "• 'atomic brain fusion' → 'atom symbol with brain silhouette as the center nucleus'\n"
            "• 'tech leaf' → 'leaf outline with circuit pattern inside'\n"
            "• 'sound mountain' → 'mountain silhouette shaped like sound wave'\n\n"
            "Output: One simple sentence describing the visual concept."
        )
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.1,  # 더 일관된 결과를 위해 낮춤
            max_tokens=50     # 더 간결한 답변을 위해 줄임
        )
        
        result = response.choices[0].message.content.strip()
        print(f"🎨 생성된 설계도: {result}")
        return result
        
    except Exception as e:
        print(f"⚠️ GPT 설계도 생성 실패. 원문 사용: {user_input} ({e})")
        return user_input

def generate_symbol_logo_prompt(core_object: str, colors: List[str]) -> str:
    """
    DALL-E 3에 최적화된 로고 프롬프트 생성
    """
    try:
        print("🎨 로고 설계도를 바탕으로 최종 프롬프트 생성 중...")
        
        # 1. 구체적인 시각적 설계도 생성
        visual_blueprint = compress_scene_with_gpt(core_object)
        
        # 2. 색상 변환
        color_name = hex_to_color_name(colors[0]) if colors else "black"
        print(f"🎨 색상 변환: {colors[0] if colors else 'N/A'} → {color_name}")
        
        # 3. DALL-E 3에 최적화된 프롬프트 구조
        # 더 단순하고 직접적인 지시
        final_prompt = (
            f"A simple flat vector logo of {visual_blueprint}. "
            f"Single {color_name} color on white background. "
            f"Minimalist style, clean lines, no shadows or gradients. "
            f"Professional logo design."
        )
        
        print(f"🧾 최종 DALL-E 프롬프트:\n{final_prompt}\n")
        return final_prompt
        
    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ GPT 프롬프트 생성 실패:\n{tb}")
        sys.stderr.write(tb + "\n")
        raise RuntimeError("DALL-E 프롬프트 생성 실패")

def generate_logo_with_fallback(core_object: str, colors: List[str]) -> str:
    """
    메인 프롬프트로 실패시 백업 프롬프트 사용
    """
    try:
        # 메인 프롬프트 시도
        return generate_symbol_logo_prompt(core_object, colors)
    except Exception as e:
        print(f"⚠️ 메인 프롬프트 생성 실패, 백업 프롬프트 사용: {e}")
        
        # 백업 프롬프트 - 더 간단한 버전
        color_name = hex_to_color_name(colors[0]) if colors else "black"
        backup_prompt = (
            f"Simple {color_name} logo icon of {core_object}. "
            f"Flat vector style, white background, minimal design."
        )
        
        print(f"🔄 백업 프롬프트: {backup_prompt}")
        return backup_prompt

# 추가 유틸리티 함수들
def validate_color_format(color_list: List[str]) -> List[str]:
    """색상 형식 검증 및 정규화"""
    validated_colors = []
    for color in color_list:
        # # 제거 및 대문자 변환
        clean_color = color.replace("#", "").upper()
        # 6자리 hex 코드 검증
        if len(clean_color) == 6 and all(c in '0123456789ABCDEF' for c in clean_color):
            validated_colors.append(clean_color)
        else:
            print(f"⚠️ 잘못된 색상 코드: {color}, 기본값 사용")
            validated_colors.append("000000")  # 기본값: 검정
    return validated_colors

def get_prompt_variations(core_object: str, color: str) -> List[str]:
    """다양한 프롬프트 변형 생성 (A/B 테스트용)"""
    color_name = hex_to_color_name(color)
    visual_blueprint = compress_scene_with_gpt(core_object)
    
    variations = [
        # 변형 1: 기본
        f"A simple flat vector logo of {visual_blueprint}. Single {color_name} color on white background. Minimalist style, clean lines, no shadows or gradients. Professional logo design.",
        
        # 변형 2: 더 구체적
        f"Minimalist {color_name} logo icon: {visual_blueprint}. Flat 2D vector art, solid color, white background, simple geometric shapes.",
        
        # 변형 3: 스타일 강조
        f"Clean {color_name} logomark featuring {visual_blueprint}. Modern flat design, bold simple lines, professional branding style, isolated on white."
    ]
    
    return variations

# 테스트 함수
def test_prompt_generation():
    """프롬프트 생성 테스트"""
    test_cases = [
        ("atomic brain fusion", ["A855F7"]),
        ("tech leaf", ["10B981"]),
        ("sound wave mountain", ["3B82F6"]),
    ]
    
    for concept, colors in test_cases:
        print(f"\n🧪 테스트: {concept}")
        print(f"색상: {colors}")
        
        try:
            prompt = generate_symbol_logo_prompt(concept, colors)
            print(f"✅ 결과: {prompt}")
        except Exception as e:
            print(f"❌ 실패: {e}")

if __name__ == "__main__":
    test_prompt_generation()