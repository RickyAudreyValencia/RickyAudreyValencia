from __future__ import annotations

import argparse
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


GOLD = (232, 194, 122)


def make_frame(base: Image.Image, index: int, frame_count: int) -> Image.Image:
    width, height = base.size
    phase = index / frame_count

    brightness = 1.0 + 0.025 * math.sin(phase * math.tau)
    frame = ImageEnhance.Brightness(base).enhance(brightness).convert("RGBA")

    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    ring_alpha = int(22 + 18 * (0.5 + 0.5 * math.sin(phase * math.tau)))
    ring_box = (
        int(width * 0.166),
        int(height * 0.072),
        int(width * 0.505),
        int(height * 0.925),
    )
    glow_draw.ellipse(ring_box, outline=(*GOLD, ring_alpha), width=max(5, width // 170))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(8, width // 100)))
    frame = Image.alpha_composite(frame, glow)

    sheen = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sheen_draw = ImageDraw.Draw(sheen)
    center_x = int(-width * 0.25 + phase * width * 1.5)
    band_width = max(45, width // 16)
    sheen_draw.polygon(
        [
            (center_x - band_width, 0),
            (center_x, 0),
            (center_x + band_width, height),
            (center_x, height),
        ],
        fill=(255, 225, 165, 22),
    )
    sheen = sheen.filter(ImageFilter.GaussianBlur(radius=max(12, width // 75)))
    frame = Image.alpha_composite(frame, sheen)

    sparkles = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sparkle_draw = ImageDraw.Draw(sparkles)
    points = (
        (0.115, 0.855, 0.05),
        (0.185, 0.905, 0.28),
        (0.425, 0.115, 0.52),
        (0.655, 0.845, 0.76),
        (0.875, 0.745, 0.91),
    )
    for x_ratio, y_ratio, offset in points:
        intensity = max(0.0, math.sin((phase + offset) * math.tau)) ** 4
        if intensity == 0:
            continue
        radius = max(1, int(width / 500 + intensity * width / 500))
        alpha = int(35 + intensity * 150)
        x, y = int(width * x_ratio), int(height * y_ratio)
        sparkle_draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*GOLD, alpha))

    sparkles = sparkles.filter(ImageFilter.GaussianBlur(radius=max(1, width // 900)))
    return Image.alpha_composite(frame, sparkles).convert("RGB")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a subtle looping README banner GIF.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--frames", type=int, default=36)
    parser.add_argument("--duration", type=int, default=85, help="Milliseconds per frame")
    args = parser.parse_args()

    source = Image.open(args.input).convert("RGB")
    height = round(source.height * args.width / source.width)
    base = source.resize((args.width, height), Image.Resampling.LANCZOS)
    frames = [make_frame(base, index, args.frames) for index in range(args.frames)]

    palette = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    quantized = [
        frame.quantize(palette=palette, dither=Image.Dither.NONE)
        for frame in frames
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    quantized[0].save(
        args.output,
        save_all=True,
        append_images=quantized[1:],
        duration=args.duration,
        loop=0,
        optimize=True,
        disposal=2,
    )


if __name__ == "__main__":
    main()
