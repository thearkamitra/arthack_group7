"""Normalize transparent foregrounds without stretching or overwriting sources."""

import json
from pathlib import Path

from PIL import Image

from .images import validate_rgba


def normalize_pair(one: Path, two: Path, output: Path, size: int = 128) -> tuple[Path, Path]:
    if size < 16:
        raise ValueError("Canvas must be at least 16 pixels")
    crops = []
    records = []
    for source in (one, two):
        validate_rgba(source)
        with Image.open(source) as image:
            image.load()
            bounds = image.getchannel("A").point(lambda x: 255 if x > 127 else 0).getbbox()
            if bounds is None:
                raise ValueError("No foreground")
            crops.append(image.crop(bounds))
            records.append(
                {
                    "source": str(source.resolve()),
                    "source_size": list(image.size),
                    "crop": list(bounds),
                }
            )
    # One common foreground width, constrained by the taller crop: no clipping.
    width = max(1, int(min(size * 0.8, *(size * 0.9 * c.width / c.height for c in crops))))
    output.mkdir(parents=True, exist_ok=False)
    destinations = []
    for index, (crop, record) in enumerate(zip(crops, records), 1):
        height = max(1, round(crop.height * width / crop.width))
        resized = crop.resize((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        offset = ((size - width) // 2, (size - height) // 2)
        canvas.paste(resized, offset)
        destination = output / f"input_{index}_rgba.png"
        with destination.open("xb") as stream:
            canvas.save(stream, format="PNG")
        record.update(output=str(destination), resized_size=[width, height], offset=list(offset))
        destinations.append(destination)
    (output / "normalization.json").write_text(
        json.dumps(
            {
                "method": "alpha>127 crop; common width; aspect-preserving LANCZOS; centered transparent canvas",
                "canvas": [size, size],
                "foreground_width": width,
                "images": records,
                "note": "Resampling changes derived pixels; source files are unchanged.",
            },
            indent=2,
        )
    )
    return destinations[0], destinations[1]
