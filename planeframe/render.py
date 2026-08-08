from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_canvas():
    img = Image.new(mode = "RGB", size = (1200, 1600), color = (141, 223, 247))
    return img


def draw_text(img):
    draw = ImageDraw.Draw(img)
    font1 = ImageFont.truetype("assets/fonts/Inter_18pt-SemiBold.ttf", 90)
    draw.text((10,10), "Airplane", font=font1, fill=(0, 0, 0))
    return img


if __name__ == "__main__":
    img = create_canvas()
    img = draw_text(img)
    img.show()