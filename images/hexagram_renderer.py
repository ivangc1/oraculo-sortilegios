"""Renderer de hexagramas I Ching: 1 o 2 hexagramas según líneas mutables.

Líneas yang (7,9): línea continua ──────
Líneas yin (8,6):  línea partida ─── ───
Líneas mutables: marcadas con círculo (9) o X (6)
"""

from io import BytesIO
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

_FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSans-Regular.ttf"

# Colores
_BG = (25, 20, 30)
_YANG_COLOR = (220, 200, 160)
_YIN_COLOR = (220, 200, 160)
_MUTABLE_COLOR = (200, 100, 80)
_TEXT_COLOR = (200, 185, 150)
_ARROW_COLOR = (180, 160, 120)


def _get_font(size: int = 18) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(_FONT_PATH), size=size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _draw_hexagram(
    draw: ImageDraw.Draw,
    lines: list[int],
    x: int,
    y: int,
    width: int = 200,
    line_h: int = 15,
    gap: int = 12,
    show_mutables: bool = True,
) -> int:
    """Dibuja un hexagrama en las coordenadas dadas. Devuelve alto total."""
    # Las líneas se dibujan de arriba abajo (línea 6 arriba, línea 1 abajo)
    total_h = 0
    for i in range(5, -1, -1):
        line = lines[i]
        ly = y + (5 - i) * (line_h + gap)
        is_yang = line in (7, 9)
        is_mutable = line in (6, 9)

        color = _MUTABLE_COLOR if (is_mutable and show_mutables) else _YANG_COLOR

        if is_yang:
            # Línea continua
            draw.rectangle([(x, ly), (x + width, ly + line_h)], fill=color)
        else:
            # Línea partida (dos segmentos con hueco)
            segment_w = (width - 20) // 2
            draw.rectangle([(x, ly), (x + segment_w, ly + line_h)], fill=color)
            draw.rectangle([(x + segment_w + 20, ly), (x + width, ly + line_h)], fill=color)

        # Marca de mutable
        if is_mutable and show_mutables:
            marker_x = x + width + 10
            marker_y = ly + line_h // 2
            if line == 9:
                # Círculo para yang viejo
                draw.ellipse(
                    [(marker_x - 6, marker_y - 6), (marker_x + 6, marker_y + 6)],
                    outline=_MUTABLE_COLOR, width=2,
                )
            else:  # line == 6
                # X para yin viejo
                draw.line([(marker_x - 5, marker_y - 5), (marker_x + 5, marker_y + 5)],
                          fill=_MUTABLE_COLOR, width=2)
                draw.line([(marker_x + 5, marker_y - 5), (marker_x - 5, marker_y + 5)],
                          fill=_MUTABLE_COLOR, width=2)

        total_h = (5 - i + 1) * (line_h + gap)

    return total_h


def render_hexagram(hexagram: dict) -> BytesIO | None:
    """Renderiza 1 o 2 hexagramas según haya mutables.

    Sin mutables: solo hexagrama primario.
    Con mutables: primario → flecha → derivado.
    """
    try:
        lines = hexagram["lines"]
        has_derived = hexagram["derived"] is not None
        font = _get_font(18)
        font_sm = _get_font(14)

        hex_w = 200
        hex_h = 6 * (15 + 12)
        mutable_margin = 30  # Espacio para marcas de mutables

        if has_derived:
            arrow_w = 60
            padding = 40
            canvas_w = padding + hex_w + mutable_margin + arrow_w + hex_w + padding
        else:
            padding = 60
            canvas_w = padding + hex_w + mutable_margin + padding

        label_h = 80  # Espacio para nombre debajo
        canvas_h = padding + hex_h + label_h + padding

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=_BG)
        draw = ImageDraw.Draw(canvas)

        # Hexagrama primario
        hx = padding
        hy = padding
        _draw_hexagram(draw, lines, hx, hy, width=hex_w, show_mutables=has_derived)

        # Etiqueta primario
        p_info = hexagram.get("primary_spanish", "")
        p_num = hexagram.get("primary", "")
        p_name = hexagram.get("primary_name", "")
        p_chinese = hexagram.get("primary_chinese", "")
        label1 = f"{p_num}. {p_name} {p_chinese}"
        label2 = p_info
        bbox = draw.textbbox((0, 0), label1, font=font)
        tw = bbox[2] - bbox[0]
        lx = hx + (hex_w - tw) // 2
        draw.text((lx, hy + hex_h + 10), label1, fill=_TEXT_COLOR, font=font)
        if label2:
            bbox2 = draw.textbbox((0, 0), label2, font=font_sm)
            tw2 = bbox2[2] - bbox2[0]
            lx2 = hx + (hex_w - tw2) // 2
            draw.text((lx2, hy + hex_h + 35), label2, fill=_TEXT_COLOR, font=font_sm)

        if has_derived:
            # Flecha →
            arrow_x = padding + hex_w + mutable_margin + 5
            arrow_y = hy + hex_h // 2
            draw.line([(arrow_x, arrow_y), (arrow_x + arrow_w - 15, arrow_y)],
                      fill=_ARROW_COLOR, width=3)
            # Punta de flecha
            draw.polygon([
                (arrow_x + arrow_w - 15, arrow_y - 8),
                (arrow_x + arrow_w, arrow_y),
                (arrow_x + arrow_w - 15, arrow_y + 8),
            ], fill=_ARROW_COLOR)

            # Hexagrama derivado (líneas transformadas)
            derived_lines = []
            for line in lines:
                if line == 9:
                    derived_lines.append(8)  # yang viejo → yin joven
                elif line == 6:
                    derived_lines.append(7)  # yin viejo → yang joven
                else:
                    derived_lines.append(line)

            d_hx = padding + hex_w + mutable_margin + arrow_w
            _draw_hexagram(draw, derived_lines, d_hx, hy, width=hex_w, show_mutables=False)

            # Etiqueta derivado
            d_info = hexagram.get("derived_spanish", "")
            d_num = hexagram.get("derived", "")
            d_name = hexagram.get("derived_name", "")
            d_chinese = hexagram.get("derived_chinese", "")
            d_label1 = f"{d_num}. {d_name} {d_chinese}"
            d_label2 = d_info or ""
            bbox = draw.textbbox((0, 0), d_label1, font=font)
            tw = bbox[2] - bbox[0]
            dlx = d_hx + (hex_w - tw) // 2
            draw.text((dlx, hy + hex_h + 10), d_label1, fill=_TEXT_COLOR, font=font)
            if d_label2:
                bbox2 = draw.textbbox((0, 0), d_label2, font=font_sm)
                tw2 = bbox2[2] - bbox2[0]
                dlx2 = d_hx + (hex_w - tw2) // 2
                draw.text((dlx2, hy + hex_h + 35), d_label2, fill=_TEXT_COLOR, font=font_sm)

        buf = BytesIO()
        canvas.convert("RGB").save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return buf

    except Exception as e:
        logger.error(f"Error rendering hexagram: {e}")
        return None


def build_caption(hexagram: dict) -> str:
    """Caption descriptivo para la imagen del hexagrama."""
    parts = []
    p = hexagram
    parts.append(f"Hexagrama {p['primary']}: {p['primary_name']} {p.get('primary_chinese', '')} — {p.get('primary_spanish', '')}")

    if p["mutable_lines"]:
        parts.append(f"Líneas mutables: {', '.join(str(l) for l in p['mutable_lines'])}")

    if p["derived"]:
        parts.append(f"→ Hexagrama {p['derived']}: {p['derived_name']} {p.get('derived_chinese', '')} — {p.get('derived_spanish', '')}")
    else:
        parts.append("Sin líneas mutables — situación estable")

    return "\n".join(parts)


def build_text_fallback(hexagram: dict) -> str:
    """Texto descriptivo si el renderer falla."""
    lines_desc = []
    for i, line in enumerate(hexagram["lines"], 1):
        line_type = {6: "⚋ yin viejo (mutable)", 7: "⚊ yang joven",
                     8: "⚋ yin joven", 9: "⚊ yang viejo (mutable)"}
        lines_desc.append(f"  Línea {i}: {line_type.get(line, str(line))}")

    parts = [
        f"☯ Hexagrama {hexagram['primary']}: {hexagram['primary_name']} — {hexagram.get('primary_spanish', '')}",
        "",
        *lines_desc,
    ]

    if hexagram["derived"]:
        parts.append(f"\n→ Transforma a: {hexagram['derived']}: {hexagram['derived_name']} — {hexagram.get('derived_spanish', '')}")
    else:
        parts.append("\nSin mutables — situación estable, sin transformación.")

    return "\n".join(parts)
