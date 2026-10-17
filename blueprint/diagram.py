"""Draw the sample architecture diagram the demo photograph stands in for."""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

BOXES = {
    "Billing": (70, 50, 250, 120),
    "Auth": (70, 390, 250, 120),
    "Payments": (520, 50, 280, 120),
    "Notifications": (520, 390, 320, 120),
}


def render_diagram(path: Path) -> None:
    image = Image.new("RGB", (960, 580), "white")
    draw = ImageDraw.Draw(image)
    font = _font(40)
    boxes = {label: _rect(bounds) for label, bounds in BOXES.items()}
    for label, rect in boxes.items():
        draw.rounded_rectangle(rect, radius=18, outline="#111827", width=5, fill="#f8fafc")
        _center_text(draw, rect, label, font)

    _arrow(draw, _bottom(boxes["Billing"], 0), _top(boxes["Auth"], 0))
    _arrow(draw, _right(boxes["Billing"], 0), _left(boxes["Payments"], 0))
    _arrow(draw, _bottom(boxes["Payments"], -36), _top(boxes["Notifications"], -36))
    _arrow(draw, _top(boxes["Notifications"], 36), _bottom(boxes["Payments"], 36))

    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, "PNG")


def _rect(bounds: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    x, y, w, h = bounds
    return (x, y, x + w, y + h)


def _center_text(draw: ImageDraw.ImageDraw, rect: tuple[int, int, int, int], label: str, font) -> None:
    box = draw.textbbox((0, 0), label, font=font)
    width = box[2] - box[0]
    height = box[3] - box[1]
    x = rect[0] + (rect[2] - rect[0] - width) / 2
    y = rect[1] + (rect[3] - rect[1] - height) / 2 - box[1]
    draw.text((x, y), label, fill="#111827", font=font)


def _font(size: int) -> ImageFont.ImageFont:
    for candidate in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _left(rect: tuple[int, int, int, int], dy: int) -> tuple[float, float]:
    return (rect[0], (rect[1] + rect[3]) / 2 + dy)


def _right(rect: tuple[int, int, int, int], dy: int) -> tuple[float, float]:
    return (rect[2], (rect[1] + rect[3]) / 2 + dy)


def _top(rect: tuple[int, int, int, int], dx: int) -> tuple[float, float]:
    return ((rect[0] + rect[2]) / 2 + dx, rect[1])


def _bottom(rect: tuple[int, int, int, int], dx: int) -> tuple[float, float]:
    return ((rect[0] + rect[2]) / 2 + dx, rect[3])


def _arrow(draw: ImageDraw.ImageDraw, start: tuple[float, float], end: tuple[float, float]) -> None:
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    inset = 8
    tip = (end[0] - inset * math.cos(angle), end[1] - inset * math.sin(angle))
    tail = (start[0] + inset * math.cos(angle), start[1] + inset * math.sin(angle))
    color = "#1d4ed8"
    draw.line([tail, tip], fill=color, width=6)
    length = 20
    spread = 0.42
    left = (tip[0] - length * math.cos(angle - spread), tip[1] - length * math.sin(angle - spread))
    right = (tip[0] - length * math.cos(angle + spread), tip[1] - length * math.sin(angle + spread))
    draw.polygon([tip, left, right], fill=color)
