"""Pixel-preserving background segmentation."""

import os
from pathlib import Path

from PIL import Image, ImageChops, ImageOps


def apply_mask(source: Image.Image, mask: Image.Image) -> Image.Image:
    """Keep RGB unchanged and intersect the mask with existing transparency."""
    if source.size != mask.size:
        raise ValueError("Mask dimensions must match the source image")
    result = source.convert("RGBA")
    result.putalpha(ImageChops.multiply(result.getchannel("A"), mask.convert("L")))
    return result


def remove_background(
    source: Path, destination: Path, cache: Path, model: str = "u2net_human_seg"
) -> Path:
    if source.resolve() == destination.resolve() or destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    if destination.suffix.lower() != ".png":
        raise ValueError("Transparent output must have a .png extension")
    with Image.open(source) as image:
        original = ImageOps.exif_transpose(image).convert("RGBA")
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(cache.resolve())
    os.environ.setdefault("NUMBA_CACHE_DIR", str(cache.resolve() / "numba"))
    from rembg import new_session, remove

    session = new_session(model, providers=["CPUExecutionProvider"])
    mask = remove(original.convert("RGB"), session=session, only_mask=True)
    result = apply_mask(original, mask)
    alpha = result.getchannel("A")
    if alpha.getextrema()[0] >= 128 or alpha.getextrema()[1] <= 128:
        raise ValueError("Segmentation lacks foreground or background; inspect the input")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents accidental replacement, including concurrent jobs.
    with destination.open("xb") as stream:
        result.save(stream, format="PNG")
    return destination


def validate_rgba(path: Path) -> None:
    with Image.open(path) as image:
        if image.mode != "RGBA":
            raise ValueError(f"{path} must be an RGBA PNG")
        if image.format != "PNG":
            raise ValueError(f"{path} must be a PNG file")
        low, high = image.getchannel("A").getextrema()
        if low >= 128 or high <= 128:
            raise ValueError(f"{path} needs foreground and transparent background")
