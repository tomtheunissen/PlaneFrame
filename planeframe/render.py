from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from planeframe.config import ROOT, FONTS, REGULAR, SEMIBOLD, OUTPUT


def create_canvas():
    img = Image.new(mode = "RGB", size = (1200, 1600), color = (186, 226, 245))
    return img


def draw_text(img, planes):
    draw = ImageDraw.Draw(img)
    font1 = ImageFont.truetype(SEMIBOLD, 55)
    coord_y = 500

    for plane in planes:
        draw.text((50, coord_y), plane.description, font=font1, fill=(0, 0, 0))
        coord_y = coord_y + 400
    return img


def draw_plane(img, planes):
    draw = ImageDraw.Draw(img)
    coord_y = 250

    for plane in planes:
        type_path = image_for(plane)
        plane_img = Image.open(type_path).convert("RGBA")

        w, h = plane_img.size
        new_h = 220
        new_w = int(w * (new_h / h))

        plane_img = plane_img.resize((new_w, new_h))

        img.paste(plane_img, (50, coord_y), plane_img)
        coord_y = coord_y + 400
    return img

if __name__ == "__main__":
    from planeframe.models import aircraft_from_response
    from planeframe.sources.airplanes_live import load_sample
    from planeframe.filters import select_for_display
    from planeframe.imagery import image_for

    result = load_sample("data/samples/20260808-163007.json")
    planes = aircraft_from_response(result)
    planes = select_for_display(planes)

    img = create_canvas()
    img = draw_text(img, planes)
    img = draw_plane(img, planes)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT / "planes.png")