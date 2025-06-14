from PIL import Image, ImageDraw, ImageFont

def apply_rotated_watermark(
    img: Image.Image,
    text="BRANDIEAI",
    font_path="backend/assets/fonts/Aldrich-Regular.ttf"
) -> Image.Image:
    width, height = img.size
    font_size = int(min(width, height) * 0.05)
    font = ImageFont.truetype(font_path, font_size)

    # 대각선 기준 더 넉넉한 워터마크 레이어 생성
    diagonal = int((width**2 + height**2) ** 0.5)
    extended_size = diagonal * 2  # 넉넉히 확보
    watermark_layer = Image.new("RGBA", (extended_size, extended_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(watermark_layer)

    # 글자 간격 증가 (겹침 방지)
    step_x = int(font_size * 6)
    step_y = int(font_size * 6)

    for y in range(0, extended_size, step_y):
        for x in range(0, extended_size, step_x):
            draw.text((x, y), text, font=font, fill=(255, 0, 0, 40))  # 투명도 40

    # 회전 (확장 없이 그대로)
    rotated = watermark_layer.rotate(45, expand=False)

    # 중심 기준 crop
    left = (extended_size - width) // 2
    top = (extended_size - height) // 2
    cropped = rotated.crop((left, top, left + width, top + height))

    # 이미지에 합성
    img_rgba = img.convert("RGBA")
    final = Image.alpha_composite(img_rgba, cropped)
    return final.convert("RGB")