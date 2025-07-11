import os
import sys
import traceback
from typing import List, Dict, Optional
from openai import OpenAI

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_professional_logo_concept(user_input: str, brand_name: str = None) -> Dict[str, str]:
    """
    사용자 입력을 전문적인 로고 디자인 컨셉으로 변환합니다.
    GPT 대화방에서 성공했던 방식을 모방하여 체계적인 로고 설계를 수행합니다.
    """
    try:
        system_prompt = """You are a world-class logo design consultant working with premium brands. 
Your task is to transform user concepts into professional logo design specifications that will produce 
clean, memorable, and commercially viable logos.

CRITICAL: Focus on creating ICONIC SYMBOLS, not illustrations or complex scenes.

### Your Process:
1. **Brand Analysis**: Understand the core concept and brand personality
2. **Symbol Strategy**: Design a simple, memorable symbol that captures the essence
3. **Professional Specifications**: Provide clear design directions

### Output Format (JSON):
{
  "symbol_concept": "Simple, iconic symbol description (max 15 words)",
  "design_style": "Professional logo style specification",
  "color_strategy": "Primary color recommendation with reasoning",
  "brand_personality": "3-4 words describing brand feel"
}

### Excellence Examples:
- Input: "atomic brain fusion" → Symbol: "Brain silhouette with orbital rings around it"
- Input: "banana kick" → Symbol: "Stylized banana with motion lines suggesting impact"
- Input: "tech leaf" → Symbol: "Geometric leaf with circuit pattern integration"

Focus on SIMPLICITY and MEMORABILITY. Think Nike swoosh, Apple logo, McDonald's arches level of iconic simplicity."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Brand concept: {user_input}" + (f"\nBrand name: {brand_name}" if brand_name else "")}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.3,
            max_tokens=200
        )
        
        # JSON 응답 파싱 시도
        try:
            import json
            result = json.loads(response.choices[0].message.content.strip())
            return result
        except:
            # JSON 파싱 실패 시 기본값 반환
            return {
                "symbol_concept": response.choices[0].message.content.strip()[:100],
                "design_style": "minimalist professional logo",
                "color_strategy": "single bold color",
                "brand_personality": "modern, professional, memorable"
            }
            
    except Exception as e:
        print(f"⚠️ 로고 컨셉 생성 실패: {e}")
        return {
            "symbol_concept": user_input,
            "design_style": "minimalist professional logo", 
            "color_strategy": "single bold color",
            "brand_personality": "modern, clean, professional"
        }

def generate_premium_logo_prompt(
    concept: str, 
    brand_name: str = None, 
    primary_color: str = None
) -> str:
    """
    프리미엄 로고 생성을 위한 최적화된 DALL-E 프롬프트를 생성합니다.
    심볼 로고만 생성하는 구조로 단순화됨.
    """
    try:
        print("🎨 프리미엄 로고 컨셉 분석 중...")
        
        # 1단계: 전문적인 로고 컨셉 생성
        logo_concept = create_professional_logo_concept(concept, brand_name)
        
        print(f"✅ 심볼 컨셉: {logo_concept['symbol_concept']}")
        print(f"✅ 디자인 스타일: {logo_concept['design_style']}")
        print(f"✅ 브랜드 개성: {logo_concept['brand_personality']}")
        
        # 2단계: 색상 전략 결정
        if primary_color:
            color_instruction = f"in {primary_color} color"
        elif logo_concept.get('color_strategy'):
            color_instruction = f"in {logo_concept['color_strategy']}"
        else:
            color_instruction = "in a single professional color"
        
        # 3단계: 최종 프롬프트 (심볼 단일, 텍스트/워드마크 없음)
        final_prompt = f"""Professional logo design: {logo_concept['symbol_concept']}, 
minimalist professional logo, {color_instruction}, 
ultra-clean vector style, perfect symmetry, iconic symbol, 
minimal details, scalable design, corporate quality,
isolated on pure white background,
--no text, letters, words, shading, shadows, gradients, 3d effects, photorealistic details, complex illustrations"""
        
        print(f"🔧 최종 로고 프롬프트:\n{final_prompt}\n")
        return final_prompt
            
    except Exception as e:
        tb = traceback.format_exc()
        print(f"❌ 프리미엄 로고 프롬프트 생성 실패:\n{tb}")
        sys.stderr.write(tb + "\n")
        raise RuntimeError("프리미엄 로고 프롬프트 생성 실패")

def generate_logo_variations(concept: str, brand_name: str = None, colors: List[str] = None) -> List[str]:
    """
    다양한 색상 버전의 로고 프롬프트를 생성합니다. (스타일 변형 삭제, 심볼 전용)
    """
    variations = []
    color_list = colors if colors else [None]
    
    for color in color_list:
        try:
            prompt = generate_premium_logo_prompt(concept, brand_name, color)
            variations.append({
                "color": color,
                "prompt": prompt
            })
        except Exception as e:
            print(f"⚠️ {color} 색상 버전 생성 실패: {e}")
            
    return variations

# 사용 예시
if __name__ == "__main__":
    # 기본 사용법
    test_concept = "atomic brain fusion"
    test_brand = "NeuroTech"
    
    print("=== 프리미엄 로고 생성 테스트 ===")
    try:
        # 단일 로고 생성
        logo_prompt = generate_premium_logo_prompt(
            concept=test_concept,
            brand_name=test_brand,
            primary_color="electric blue"
        )
        print(f"생성된 프롬프트: {logo_prompt}")
        
        # 다양한 색상 변형 생성
        print("\n=== 색상 변형 생성 ===")
        variations = generate_logo_variations(test_concept, test_brand, ["purple", "blue"])
        for i, variation in enumerate(variations):
            print(f"\n{i+1}. {variation['color'] or 'DEFAULT'} 컬러:")
            print(variation['prompt'])
            
    except Exception as e:
        print(f"테스트 실패: {e}")