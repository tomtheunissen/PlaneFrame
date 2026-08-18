"""Compose the image the frame displays."""

from PIL import Image, ImageDraw, ImageFont

from planeframe.config import OUTPUT, SEMIBOLD, settings
from planeframe.imagery import image_for
from planeframe.models import Aircraft

TITLE_FONT = ImageFont.truetype(SEMIBOLD, settings.title_size)


def create_canvas() -> Image.Image:
    """A blank frame in the background colour."""
    return Image.new("RGB", (settings.width, settings.height), settings.background)


def band_height(count: int) -> float:
    """How much vertical space each aircraft gets.

    Derived from the number of aircraft rather than fixed, so two fill
    the frame the same way three do instead of leaving a gap at the
    bottom.
    """
    usable = settings.height - 2 * settings.margin
    return usable / count


def scaled(plane: Aircraft) -> Image.Image | None:
    """Load this aircraft's illustration at display height.

    LANCZOS matters here: the source drawings are around 2500 pixels
    wide and end up near 900, and the default filter leaves the edges
    visibly stepped at that reduction.
    """
    path = image_for(plane)
    if path is None:
        return None

    img = Image.open(path).convert("RGBA")
    width, height = img.size
    new_width = int(width * (settings.plane_height / height))
    return img.resize((new_width, settings.plane_height), Image.LANCZOS)


def draw_aircraft(img: Image.Image, planes: list[Aircraft]) -> Image.Image:
    """Draw every aircraft with its label, one per band.

    Illustration and text are placed in the same pass because they have
    to stay aligned, and computing the same position twice is how they
    drift apart.
    """
    if not planes:
        return img

    draw = ImageDraw.Draw(img)
    height = band_height(len(planes))
    block = settings.plane_height + settings.gap + settings.title_size

    for index, plane in enumerate(planes):
        band_top = settings.margin + index * height
        block_top = band_top + (height - block) / 2

        illustration = scaled(plane)
        if illustration is not None:
            img.paste(illustration, (settings.margin, int(block_top)), illustration)

        label_y = block_top + settings.plane_height + settings.gap
        draw.text(
            (settings.margin, int(label_y)),
            plane.description or plane.type_code or "",
            font=TITLE_FONT,
            fill=settings.ink,
        )

    return img


def render(planes: list[Aircraft]) -> Image.Image:
    """Build the complete frame."""
    return draw_aircraft(create_canvas(), planes)


if __name__ == "__main__":
    from planeframe.config import SAMPLES
    from planeframe.filters import select_for_display
    from planeframe.models import aircraft_from_response
    from planeframe.sources.airplanes_live import load_sample

    result = load_sample(SAMPLES / "20260808-163007.json")
    planes = select_for_display(aircraft_from_response(result))

    img = render(planes)

    OUTPUT.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT / "planes.png")
    print(f"{len(planes)} aircraft rendered")