"""Build the animated GitHub statistics dashboard used in README.md."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
OUTPUT = ASSETS / "stats-dashboard-animated.gif"

SIZE = (960, 640)
FRAME_COUNT = 32
GOLD = (232, 194, 122)


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def fit_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    scale = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - size[0]) // 2
    top = (resized.height - size[1]) // 2
    return resized.crop((left, top, left + size[0], top + size[1])).convert("RGBA")


def prepare_card(path: Path, width: int) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    height = round(image.height * width / image.width)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def card_visibility(frame: int, start: int, end: int) -> float:
    intro = smoothstep((frame - start) / max(1, end - start))
    outro = 1.0 - smoothstep((frame - 25) / 6.0)
    return intro * outro


def paste_card(
    canvas: Image.Image,
    card: Image.Image,
    position: tuple[int, int],
    visibility: float,
) -> None:
    if visibility <= 0:
        return

    x, target_y = position
    y = target_y + round((1.0 - visibility) * 14)
    alpha = card.getchannel("A").point(lambda a: round(a * visibility))

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_mask = Image.new("L", canvas.size, 0)
    glow_mask.paste(alpha, (x, y))
    glow_mask = glow_mask.filter(ImageFilter.GaussianBlur(12))
    glow.putalpha(glow_mask.point(lambda a: round(a * 0.18)))
    gold_layer = Image.new("RGBA", canvas.size, (*GOLD, 0))
    gold_layer.putalpha(glow.getchannel("A"))
    canvas.alpha_composite(gold_layer)

    layer = card.copy()
    layer.putalpha(alpha)
    canvas.alpha_composite(layer, (x, y))


def add_ambient_animation(canvas: Image.Image, frame: int) -> None:
    phase = frame / FRAME_COUNT
    pulse = 0.5 + 0.5 * math.sin(phase * math.tau)

    glow = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    line_alpha = round(25 + 28 * pulse)

    # Trace the three generated dashboard frames with a restrained gold pulse.
    draw.rounded_rectangle((58, 62, 899, 298), radius=18, outline=(*GOLD, line_alpha), width=2)
    draw.rounded_rectangle((59, 316, 473, 580), radius=16, outline=(*GOLD, line_alpha), width=2)
    draw.rounded_rectangle((487, 316, 901, 580), radius=16, outline=(*GOLD, line_alpha), width=2)
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(4)))
    canvas.alpha_composite(glow)

    # A slow diagonal sheen appears only while the cards are fully visible.
    sheen_strength = smoothstep((frame - 10) / 5.0) * (1.0 - smoothstep((frame - 23) / 4.0))
    if sheen_strength > 0:
        center = round(-180 + phase * 1320)
        sheen = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        sheen_draw = ImageDraw.Draw(sheen)
        sheen_draw.polygon(
            [(center - 55, 0), (center + 10, 0), (center - 180, 640), (center - 245, 640)],
            fill=(255, 222, 155, round(18 * sheen_strength)),
        )
        canvas.alpha_composite(sheen.filter(ImageFilter.GaussianBlur(18)))

    particles = ((44, 42), (918, 48), (31, 274), (925, 302), (48, 603), (910, 596))
    particles_layer = Image.new("RGBA", SIZE, (0, 0, 0, 0))
    particles_draw = ImageDraw.Draw(particles_layer)
    for index, (x, y) in enumerate(particles):
        local = 0.5 + 0.5 * math.sin(phase * math.tau + index * 1.17)
        radius = 1 + round(local)
        particles_draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=(*GOLD, round(55 + local * 105)),
        )
    canvas.alpha_composite(particles_layer.filter(ImageFilter.GaussianBlur(1)))


def main() -> None:
    required = {
        "background": ASSETS / "stats-dashboard-background.png",
        "details": ASSETS / "stats-card-profile-details.png",
        "stats": ASSETS / "stats-card-overview.png",
        "languages": ASSETS / "stats-card-languages.png",
    }
    missing = [str(path) for path in required.values() if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing source files:\n" + "\n".join(missing))

    background = fit_cover(Image.open(required["background"]), SIZE)
    details = prepare_card(required["details"], 800)
    stats = prepare_card(required["stats"], 370)
    languages = prepare_card(required["languages"], 370)

    frames: list[Image.Image] = []
    for frame_index in range(FRAME_COUNT):
        frame = background.copy()
        add_ambient_animation(frame, frame_index)
        paste_card(frame, details, (80, 66), card_visibility(frame_index, 1, 9))
        paste_card(frame, stats, (81, 339), card_visibility(frame_index, 6, 14))
        paste_card(frame, languages, (509, 339), card_visibility(frame_index, 9, 17))
        frames.append(frame.convert("RGB"))

    palette = frames[20].quantize(colors=176, method=Image.Quantize.MEDIANCUT)
    indexed = [
        frame.quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG)
        for frame in frames
    ]
    indexed[0].save(
        OUTPUT,
        save_all=True,
        append_images=indexed[1:],
        duration=100,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print(f"Created {OUTPUT} ({OUTPUT.stat().st_size / 1024 / 1024:.2f} MiB)")


if __name__ == "__main__":
    main()
