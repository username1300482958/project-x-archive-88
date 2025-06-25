from PIL import Image, ImageDraw, ImageFont
import numpy as np # 숫자 계산을 위해 numpy 라이브러리가 필요합니다.

def get_avg_brightness(img: Image.Image) -> float:
    """이미지의 평균 밝기를 계산하는 헬퍼 함수 (0-255)"""
    # 이미지를 흑백(Luminance)으로 변환 후, numpy 배열로 만들어 평균을 계산합니다.
    im_grey = img.convert('L')
    return np.array(im_grey).mean()

def apply_rotated_watermark(
    img: Image.Image,
    text: str = "© brandieai.com", # 👈 [수정] 저작권 표시로 변경
    font_path: str = "backend/assets/fonts/Aldrich-Regular.ttf"
) -> Image.Image:
    
    # 1. 지능적인 색상 선택
    avg_brightness = get_avg_brightness(img)
    if avg_brightness > 128: # 배경이 밝으면
        watermark_color = (0, 0, 0, 30) # 은은한 검은색 (R, G, B, Alpha)
    else: # 배경이 어두우면
        watermark_color = (255, 255, 255, 25) # 은은한 흰색

    width, height = img.size
    
    # 2. 폰트 크기 및 간격 미세 조정
    font_size = int(min(width, height) * 0.045) # 기존 0.05에서 약간 줄임
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        print(f"⚠️ 폰트 파일을 찾을 수 없습니다: {font_path}. 기본 폰트를 사용합니다.")
        font = ImageFont.load_default()

    diagonal = int((width**2 + height**2) ** 0.5)
    watermark_layer = Image.new("RGBA", (diagonal * 2, diagonal * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)

    # 텍스트의 실제 렌더링 크기를 계산합니다.
    try:
        # Pillow 10.0.0 이상
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
    except AttributeError:
        # 이전 버전 Pillow
        text_width, text_height = draw.textsize(text, font=font)

    # 3. 간격을 더 넓혀 세련미 추가
    step_x = int(text_width * 1.8)
    step_y = int(text_height * 7) # 세로 간격을 더 넓힘

    # 타일링
    for y in range(0, diagonal * 2, step_y):
        for x in range(0, diagonal * 2, step_x):
            draw.text((x, y), text, font=font, fill=watermark_color)

    # 회전 및 자르기
    rotated = watermark_layer.rotate(30, expand=False, resample=Image.BICUBIC)
    
    left = (rotated.width - width) // 2
    top = (rotated.height - height) // 2
    cropped = rotated.crop((left, top, left + width, top + height))

    # 원본 이미지에 합성
    img_rgba = img.convert("RGBA")
    final_image = Image.alpha_composite(img_rgba, cropped)
    
    return final_image.convert("RGB")