"""Turn downloaded or generated side-view drawings into usable illustrations.

Removes the background with a flood fill from the corners, splits a sheet
into its separate aircraft, keeps one of them, trims the empty space and
optionally mirrors the result.

Flood fill is used rather than subject detection: it starts at the edges
and stops at the first pixel that differs, so it can never reach the thin
antennas, door outlines and small markings inside the drawing.

The destination follows the filename. A hyphen means a livery, anything
else is a plain type template:

    RYR-B738.png  ->  assets/aircraft/livery/RYR-B738.png
    B738.png      ->  assets/aircraft/type/B738.png

Files whose output already exists are skipped, so the whole raw directory
can be run again after adding one drawing to it. Pass --force to redo
them, for instance after changing the edge settings.

Run from the project root:

    python -m tools.prepare_images assets/aircraft/raw
    python -m tools.prepare_images assets/aircraft/raw/B738.jpg --mirror
    python -m tools.prepare_images assets/aircraft/raw --erode 3 --force
"""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from planeframe.imagery import LIVERY_IMAGES, TYPE_IMAGES

SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
TRANSPARENT = (0, 0, 0, 0)


def destination(stem: str) -> Path:
    """Pick the layer this illustration belongs to.

    A hyphen separates operator from type, so RYR-B738 is a livery and
    B738 is a plain template.
    """
    key = stem.upper()
    return LIVERY_IMAGES / f"{key}.png" if "-" in key else TYPE_IMAGES / f"{key}.png"


def remove_background(img: Image.Image, thresh: int, erode: int, smooth: float) -> Image.Image:
    """Flood fill from all four corners and make those pixels transparent.

    The flood fill alone leaves a coloured fringe: along the silhouette
    the drawing is antialiased, so those pixels are a blend of aircraft
    and background and differ too much to be filled. Raising the
    threshold far enough to catch them starts eating the aircraft, so the
    alpha channel is eroded instead, shaving the outermost ring of pixels
    off the mask.

    Eroding leaves a hard, stepped edge. Blurring the mask afterwards
    restores a soft one. The blur radius must stay below the erosion
    depth: it pushes the edge back outwards, and beyond the eroded ring
    lie the pixels the flood fill blacked out, which would show up as a
    dark halo.
    """
    img = img.convert("RGBA")
    width, height = img.size
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]

    for corner in corners:
        ImageDraw.floodfill(img, corner, TRANSPARENT, thresh=thresh)

    alpha = img.getchannel("A")

    for _ in range(erode):
        alpha = alpha.filter(ImageFilter.MinFilter(3))

    if smooth:
        alpha = alpha.filter(ImageFilter.GaussianBlur(min(smooth, erode - 0.5)))

    img.putalpha(alpha)
    return img


def content_bands(img: Image.Image) -> list[tuple[int, int]]:
    """Find the vertical bands that still contain something.

    Downloaded sheets usually stack two drawings of the same aircraft, one
    with the gear up and one with it down, separated by empty rows. Once
    the background is gone those rows are fully transparent, so the split
    needs no fixed measurements. Use --split when the two drawings overlap
    vertically and no empty row exists.
    """
    alpha = img.getchannel("A")
    width, height = alpha.size

    bands = []
    start = None

    for y in range(height):
        has_content = alpha.crop((0, y, width, y + 1)).getbbox() is not None
        if has_content and start is None:
            start = y
        elif not has_content and start is not None:
            bands.append((start, y))
            start = None

    if start is not None:
        bands.append((start, height))

    return bands


def prepare(
    path: Path,
    thresh: int,
    band_index: int,
    mirror: bool,
    split: float | None,
    erode: int,
    smooth: float,
) -> Image.Image:
    """Run the whole conversion for one file."""
    img = remove_background(Image.open(path), thresh, erode, smooth)

    if split:
        img = img.crop((0, 0, img.width, int(img.height * split)))

    bands = content_bands(img)
    if not bands:
        raise ValueError("nothing left after removing the background")
    if band_index >= len(bands):
        raise ValueError(f"only {len(bands)} bands found")

    top, bottom = bands[band_index]
    img = img.crop((0, top, img.width, bottom))

    box = img.getbbox()
    if box:
        img = img.crop(box)

    if mirror:
        img = img.transpose(Image.FLIP_LEFT_RIGHT)

    return img


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="image file or directory")
    parser.add_argument("--thresh", type=int, default=180, help="flood fill tolerance")
    parser.add_argument("--erode", type=int, default=2, help="pixels to shave off the edge")
    parser.add_argument("--smooth", type=float, default=1.0, help="edge blur radius")
    parser.add_argument("--band", type=int, default=0, help="which drawing to keep, 0 is top")
    parser.add_argument("--split", type=float, help="keep this fraction of the height first")
    parser.add_argument("--mirror", action="store_true", help="flip so the nose points right")
    parser.add_argument("--force", action="store_true", help="redo files that already exist")
    parser.add_argument("--dry-run", action="store_true", help="report without writing")
    args = parser.parse_args()

    if args.source.is_dir():
        files = sorted(p for p in args.source.iterdir() if p.suffix.lower() in SUFFIXES)
    else:
        files = [args.source]

    if not files:
        print("No images found.")
        return

    for path in files:
        target = destination(path.stem)

        if target.exists() and not args.force:
            print(f"{path.name:<20} {'':>13} skipped, {target.name} exists")
            continue

        try:
            img = prepare(
                path,
                args.thresh,
                args.band,
                args.mirror,
                args.split,
                args.erode,
                args.smooth,
            )
        except (OSError, ValueError) as exc:
            print(f"{path.name:<20} failed: {exc}")
            continue

        layer = target.parent.name

        if not args.dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            img.save(target)

        note = "would write" if args.dry_run else "wrote"
        print(f"{path.name:<20} {img.width:>5} x {img.height:<5} {note} {layer}/{target.name}")


if __name__ == "__main__":
    main()