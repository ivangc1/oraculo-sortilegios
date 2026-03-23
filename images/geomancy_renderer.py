"""Renderer de figuras geománticas y escudo completo."""

from io import BytesIO
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

_FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSans-Regular.ttf"
_BG = (25, 20, 30)
_DOT_COLOR = (220, 200, 160)
_TEXT_COLOR = (200, 185, 150)
_LINE_COLOR = (80, 70, 60)


def _get_font(size: int = 16) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype(str(_FONT_PATH), size=size)
    except (OSError, IOError):
        return ImageFont.load_default()


def _draw_figure(draw: ImageDraw.Draw, points: list[int],
                 x: int, y: int, cell_size: int = 30) -> None:
    """Dibuja una figura geomántica (4 filas de 1 o 2 puntos)."""
    dot_r = 5
    for row_i, count in enumerate(points):
        ry = y + row_i * cell_size
        if count == 1:
            # 1 punto centrado
            cx = x + cell_size // 2
            draw.ellipse([(cx - dot_r, ry - dot_r), (cx + dot_r, ry + dot_r)],
                         fill=_DOT_COLOR)
        else:
            # 2 puntos
            cx1 = x + cell_size // 2 - 12
            cx2 = x + cell_size // 2 + 12
            draw.ellipse([(cx1 - dot_r, ry - dot_r), (cx1 + dot_r, ry + dot_r)],
                         fill=_DOT_COLOR)
            draw.ellipse([(cx2 - dot_r, ry - dot_r), (cx2 + dot_r, ry + dot_r)],
                         fill=_DOT_COLOR)


def render_single_figure(figure: dict) -> BytesIO | None:
    """Renderiza una sola figura geomántica con nombre."""
    try:
        cell = 35
        fig_w = 60
        fig_h = 4 * cell
        padding = 30
        label_h = 50

        canvas_w = fig_w + padding * 2
        canvas_h = fig_h + padding * 2 + label_h

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=_BG)
        draw = ImageDraw.Draw(canvas)

        _draw_figure(draw, figure["points"], padding, padding, cell)

        font = _get_font(16)
        name = figure.get("spanish", figure.get("name", ""))
        bbox = draw.textbbox((0, 0), name, font=font)
        tw = bbox[2] - bbox[0]
        lx = (canvas_w - tw) // 2
        draw.text((lx, fig_h + padding + 10), name, fill=_TEXT_COLOR, font=font)

        buf = BytesIO()
        canvas.convert("RGB").save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Error rendering geomancy figure: {e}")
        return None


def render_shield(shield: dict) -> BytesIO | None:
    """Renderiza escudo geomántico completo.

    Layout:
    Fila 1: M1  M2  M3  M4  H1  H2  H3  H4
    Fila 2:   S1    S2    S3    S4
    Fila 3:     TD        TI
    Fila 4:         J
    Fila 5:         R
    """
    try:
        cell = 28
        fig_w = 60
        fig_h = 4 * cell
        gap_x = 15
        gap_y = 20
        label_h = 20
        padding = 25
        font = _get_font(12)
        font_sm = _get_font(10)

        # Fila 1: 8 figuras
        row1_w = 8 * fig_w + 7 * gap_x
        canvas_w = row1_w + padding * 2
        # 5 filas de figuras
        canvas_h = padding + 5 * (fig_h + label_h + gap_y) + padding

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=_BG)
        draw = ImageDraw.Draw(canvas)

        def draw_fig_with_label(fig, x, y):
            _draw_figure(draw, fig["points"], x, y, cell)
            name = fig.get("spanish", fig.get("name", ""))[:15]
            pos = fig.get("position", "")
            # Posición arriba
            bbox = draw.textbbox((0, 0), pos, font=font_sm)
            tw = bbox[2] - bbox[0]
            draw.text((x + (fig_w - tw) // 2, y - 15), pos, fill=(150, 140, 120), font=font_sm)
            # Nombre debajo
            bbox = draw.textbbox((0, 0), name, font=font)
            tw = bbox[2] - bbox[0]
            draw.text((x + (fig_w - tw) // 2, y + fig_h + 3), name, fill=_TEXT_COLOR, font=font)

        # Fila 1: Madres + Hijas
        y1 = padding + 15
        all_first = shield["mothers"] + shield["daughters"]
        for i, fig in enumerate(all_first):
            x = padding + i * (fig_w + gap_x)
            draw_fig_with_label(fig, x, y1)

        # Línea separadora
        sep_y = y1 + fig_h + label_h + gap_y // 2
        draw.line([(padding, sep_y), (canvas_w - padding, sep_y)], fill=_LINE_COLOR, width=1)

        # Fila 2: 4 Sobrinas (centradas entre pares)
        y2 = y1 + fig_h + label_h + gap_y
        sobrina_start = padding + (row1_w - 4 * fig_w - 3 * gap_x * 2) // 2
        for i, fig in enumerate(shield["nieces"]):
            x = sobrina_start + i * (fig_w + gap_x * 2)
            draw_fig_with_label(fig, x, y2)

        # Fila 3: 2 Testigos
        y3 = y2 + fig_h + label_h + gap_y
        testigo_start = padding + (row1_w - 2 * fig_w - gap_x * 4) // 2
        for i, fig in enumerate(shield["witnesses"]):
            x = testigo_start + i * (fig_w + gap_x * 4)
            draw_fig_with_label(fig, x, y3)

        # Fila 4: Juez
        y4 = y3 + fig_h + label_h + gap_y
        jx = padding + (row1_w - fig_w) // 2
        draw_fig_with_label(shield["judge"], jx, y4)

        # Fila 5: Reconciliador (a la derecha del juez)
        rx = jx + fig_w + gap_x * 3
        draw_fig_with_label(shield["reconciler"], rx, y4)

        buf = BytesIO()
        canvas.convert("RGB").save(buf, format="JPEG", quality=85)
        buf.seek(0)
        return buf
    except Exception as e:
        logger.error(f"Error rendering shield: {e}")
        return None


def build_caption_single(figure: dict) -> str:
    name = figure.get("spanish", figure.get("name", ""))
    points_str = " ".join("•" if p == 1 else "••" for p in figure["points"])
    return f"⊕ {name}\n{points_str}\n{figure.get('element', '')} / {figure.get('planet', '')}"


def build_caption_shield(shield: dict) -> str:
    j = shield["judge"]
    r = shield["reconciler"]
    return (
        f"⊕ Escudo geomántico\n"
        f"Juez: {j.get('spanish', j['name'])}\n"
        f"Reconciliador: {r.get('spanish', r['name'])}"
    )


def build_text_fallback_single(figure: dict) -> str:
    name = figure.get("spanish", figure.get("name", ""))
    rows = []
    for p in figure["points"]:
        rows.append("  •" if p == 1 else "  • •")
    return f"⊕ {name}\n" + "\n".join(rows)


def build_text_fallback_shield(shield: dict) -> str:
    lines = ["⊕ Escudo geomántico completo:", ""]
    for group, label in [("mothers", "Madres"), ("daughters", "Hijas"),
                         ("nieces", "Sobrinas"), ("witnesses", "Testigos")]:
        names = [f.get("spanish", f["name"]) for f in shield[group]]
        lines.append(f"{label}: {', '.join(names)}")
    lines.append(f"Juez: {shield['judge'].get('spanish', shield['judge']['name'])}")
    lines.append(f"Reconciliador: {shield['reconciler'].get('spanish', shield['reconciler']['name'])}")
    return "\n".join(lines)
