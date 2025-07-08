from PIL import Image, ImageDraw, ImageFont
import numpy as np
import xml.etree.ElementTree as ET # SVG(XML)를 다루기 위한 라이브러리

# --- 기존 PNG/JPG용 워터마크 함수 (그대로 유지) ---
def get_avg_brightness(img: Image.Image) -> float:
    """이미지의 평균 밝기를 계산하는 헬퍼 함수 (0-255)"""
    im_grey = img.convert('L')
    return np.array(im_grey).mean()

def apply_rotated_watermark(
    img: Image.Image,
    text: str = "© brandieai.com",
    font_path: str = "backend/assets/fonts/Aldrich-Regular.ttf"
) -> Image.Image:
    # ... (기존 코드는 변경 없이 그대로 둡니다) ...
    avg_brightness = get_avg_brightness(img)
    if avg_brightness > 128:
        watermark_color = (0, 0, 0, 30)
    else:
        watermark_color = (255, 255, 255, 20)
    width, height = img.size
    font_size = int(min(width, height) * 0.045)
    try:
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
    diagonal = int((width**2 + height**2) ** 0.5)
    watermark_layer = Image.new("RGBA", (diagonal * 2, diagonal * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)
    try:
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
    except AttributeError:
        text_width, text_height = draw.textsize(text, font=font)
    step_x = int(text_width * 1.2)
    step_y = int(text_height * 3)
    for y in range(0, diagonal * 2, step_y):
        for x in range(0, diagonal * 2, step_x):
            draw.text((x, y), text, font=font, fill=watermark_color)
    rotated = watermark_layer.rotate(30, expand=False, resample=Image.BICUBIC)
    left = (rotated.width - width) // 2
    top = (rotated.height - height) // 2
    cropped = rotated.crop((left, top, left + width, top + height))
    img_rgba = img.convert("RGBA")
    final_image = Image.alpha_composite(img_rgba, cropped)
    return final_image.convert("RGB")


# --- ✅ SVG 전용 워터마크 함수 (새롭게 추가) ---
def apply_watermark_to_svg(
    svg_content: str,
    text: str = "brandieai.com",
    opacity: float = 0.1,
    font_size: int = 10
) -> str:
    """
    SVG 코드(문자열)를 입력받아, 그 위에 워터마크 텍스트를 추가한 새로운 SVG 코드를 반환합니다.
    """
    try:
        # 1. SVG 코드를 XML 트리로 파싱합니다.
        # fromstring()을 사용하기 위해 바이트로 인코딩했다가 다시 작업합니다.
        svg_content_bytes = svg_content.encode('utf-8')
        root = ET.fromstring(svg_content_bytes)
        
        # SVG의 네임스페이스를 등록하여 find/findall이 정상 작동하도록 합니다.
        ET.register_namespace('', "http://www.w3.org/2000/svg")
        ns = {'svg': 'http://www.w3.org/2000/svg'}

        # 2. SVG의 크기를 가져옵니다. viewBox가 없으면 width/height를 사용합니다.
        viewBox = root.get('viewBox')
        if viewBox:
            _, _, width, height = map(float, viewBox.split())
        else:
            width = float(root.get('width', '200'))
            height = float(root.get('height', '200'))

        # 3. 워터마크 텍스트를 담을 그룹(<g>) 요소를 생성합니다.
        watermark_group = ET.Element('g', attrib={
            'opacity': str(opacity),
            'style': 'pointer-events:none;' # 워터마크가 클릭되지 않도록 설정
        })

        # 4. 캔버스 전체에 텍스트를 바둑판식으로 배치합니다.
        step_x = font_size * len(text) * 0.6
        step_y = font_size * 3

        for y in range(0, int(height + step_y), int(step_y)):
            for x in range(0, int(width + step_x), int(step_x)):
                # 각 워터마크 텍스트(<text>) 요소를 생성합니다.
                text_element = ET.Element('text', attrib={
                    'x': str(x),
                    'y': str(y),
                    'font-family': 'Arial, sans-serif',
                    'font-size': str(font_size),
                    'fill': '#000000',
                    'transform': f'rotate(-30, {x}, {y})' # 각 텍스트를 개별적으로 회전
                })
                text_element.text = text
                watermark_group.append(text_element)
        
        # 5. 생성된 워터마크 그룹을 SVG의 맨 마지막 자식으로 추가합니다.
        root.append(watermark_group)

        # 6. 수정된 XML 트리를 다시 SVG 코드(문자열)로 변환하여 반환합니다.
        return ET.tostring(root, encoding='unicode', method='xml')

    except Exception as e:
        print(f"❌ SVG 워터마크 추가 중 오류 발생: {e}")
        # 오류 발생 시 원본 SVG 내용을 그대로 반환합니다.
        return svg_content
