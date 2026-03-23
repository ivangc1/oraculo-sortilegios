"""Composiciones de tarot: 1 carta, 3 cartas, Cruz Celta.

JPEG con verificación <10MB. BytesIO cerrado tras envío por el caller.
Degradación a texto si falla.
"""

from io import BytesIO
from pathlib import Path

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from images.card_cache import load_card_image, invert_card_image

# Fuente para etiquetas
_FONT_PATH = Path(__file__).parent.parent / "assets" / "fonts" / "NotoSans-Regular.ttf"
_LABEL_FONT: ImageFont.FreeTypeFont | None = None


def _get_label_font(size: int = 22) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Carga fuente para etiquetas. Fallback a default si no existe."""
    global _LABEL_FONT
    if _LABEL_FONT is not None and _LABEL_FONT.size == size:
        return _LABEL_FONT
    try:
        _LABEL_FONT = ImageFont.truetype(str(_FONT_PATH), size=size)
    except (OSError, IOError):
        _LABEL_FONT = ImageFont.load_default()
    return _LABEL_FONT


def compose_to_jpeg(composition: Image.Image, quality: int = 85) -> BytesIO:
    """Convierte composición a JPEG en BytesIO. Verifica <10MB (límite Telegram)."""
    buf = BytesIO()
    composition.convert("RGB").save(buf, format="JPEG", quality=quality)

    size_mb = buf.getbuffer().nbytes / (1024 * 1024)
    if size_mb > 9.5:
        logger.warning(f"Image too large: {size_mb:.1f}MB, reducing quality")
        buf = BytesIO()
        composition.convert("RGB").save(buf, format="JPEG", quality=70)

    buf.seek(0)
    return buf


def compose_single(cards: list[dict]) -> BytesIO | None:
    """Composición de 1 carta con etiqueta."""
    try:
        card = cards[0]
        card_img = load_card_image(card["id"])
        if card["inverted"]:
            card_img = invert_card_image(card_img)

        cw, ch = card_img.size
        padding = 30
        label_h = 40
        canvas_w = cw + padding * 2
        canvas_h = ch + padding * 2 + label_h

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(25, 20, 30))
        canvas.paste(card_img, (padding, padding))

        # Etiqueta
        draw = ImageDraw.Draw(canvas)
        font = _get_label_font(20)
        label = card.get("position", "Carta")
        if card["inverted"]:
            label += " (invertida)"
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        x = (canvas_w - text_w) // 2
        draw.text((x, ch + padding + 10), label, fill=(200, 185, 150), font=font)

        return compose_to_jpeg(canvas)
    except Exception as e:
        logger.error(f"Error composing single card: {e}")
        return None


def compose_three(cards: list[dict]) -> BytesIO | None:
    """Composición de 3 cartas con etiquetas (Pasado, Presente, Futuro)."""
    try:
        images = []
        for card in cards:
            img = load_card_image(card["id"])
            if card["inverted"]:
                img = invert_card_image(img)
            images.append(img)

        cw, ch = images[0].size
        gap = 20
        padding = 30
        label_h = 40
        canvas_w = cw * 3 + gap * 2 + padding * 2
        canvas_h = ch + padding * 2 + label_h

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(25, 20, 30))
        draw = ImageDraw.Draw(canvas)
        font = _get_label_font(20)

        for i, (img, card) in enumerate(zip(images, cards)):
            x = padding + i * (cw + gap)
            y = padding
            canvas.paste(img, (x, y))

            # Etiqueta debajo
            label = card.get("position", f"Carta {i+1}")
            if card["inverted"]:
                label += " ↓"
            bbox = draw.textbbox((0, 0), label, font=font)
            text_w = bbox[2] - bbox[0]
            lx = x + (cw - text_w) // 2
            draw.text((lx, ch + padding + 10), label, fill=(200, 185, 150), font=font)

        return compose_to_jpeg(canvas)
    except Exception as e:
        logger.error(f"Error composing three cards: {e}")
        return None


def compose_celtic_cross(cards: list[dict]) -> BytesIO | None:
    """Composición Cruz Celta (10 cartas), disposición Waite.

    Layout (esquemático):
                    [5]
              [4]  [1+2]  [6]         [10]
                    [3]               [9]
                                      [8]
                                      [7]

    Carta 2 rotada 90° y escalada sobre carta 1.
    """
    try:
        if len(cards) < 10:
            logger.error(f"Celtic cross needs 10 cards, got {len(cards)}")
            return None

        imgs = []
        for card in cards:
            img = load_card_image(card["id"])
            if card["inverted"]:
                img = invert_card_image(img)
            imgs.append(img)

        cw, ch = imgs[0].size

        # Escalar cartas para que quepan (target ~250px ancho)
        target_w = 250
        scale_factor = target_w / cw
        cw_s = target_w
        ch_s = int(ch * scale_factor)

        scaled = [img.resize((cw_s, ch_s), Image.LANCZOS) for img in imgs]

        # Carta 2: rotada 90° y escalada para caber sobre carta 1
        card2_rotated = scaled[1].rotate(90, expand=True)
        r_scale = cw_s / card2_rotated.width
        card2_final = card2_rotated.resize(
            (int(card2_rotated.width * r_scale), int(card2_rotated.height * r_scale)),
            Image.LANCZOS,
        )

        gap = 15
        label_h = 25
        font = _get_label_font(16)

        # Calcular posiciones en grid
        # Cruz izquierda: 4 columnas (col 0-3), columna derecha: col 4
        col_w = cw_s + gap
        row_h = ch_s + gap + label_h

        # Centro de la cruz (carta 1) en col=1, row=1
        cross_cx = gap + col_w  # col 1
        cross_cy = gap + row_h  # row 1

        # Columna derecha (staff): 4 cartas verticales
        staff_x = gap + col_w * 3 + gap * 2
        staff_top = gap

        canvas_w = staff_x + cw_s + gap
        canvas_h = max(row_h * 3 + gap, ch_s * 4 + gap * 5 + label_h * 4) + gap

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(25, 20, 30))
        draw = ImageDraw.Draw(canvas)

        def paste_with_label(idx: int, x: int, y: int):
            canvas.paste(scaled[idx], (x, y))
            label = cards[idx].get("position", f"{idx+1}")
            if cards[idx]["inverted"]:
                label += " ↓"
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            lx = x + (cw_s - tw) // 2
            draw.text((lx, y + ch_s + 3), label, fill=(200, 185, 150), font=font)

        # Cruz central
        # Carta 1 (centro)
        paste_with_label(0, cross_cx, cross_cy)

        # Carta 2 (cruce, rotada sobre carta 1)
        c2x = cross_cx + (cw_s - card2_final.width) // 2
        c2y = cross_cy + (ch_s - card2_final.height) // 2
        canvas.paste(card2_final, (c2x, c2y))
        # Etiqueta carta 2
        c2_label = cards[1].get("position", "2")
        if cards[1]["inverted"]:
            c2_label += " ↓"
        bbox = draw.textbbox((0, 0), c2_label, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(
            (cross_cx + (cw_s - tw) // 2, cross_cy + ch_s + 3),
            c2_label,
            fill=(170, 155, 130),
            font=font,
        )

        # Carta 3 (base, debajo)
        paste_with_label(2, cross_cx, cross_cy + row_h)

        # Carta 4 (pasado, izquierda)
        paste_with_label(3, cross_cx - col_w, cross_cy)

        # Carta 5 (corona, arriba)
        paste_with_label(4, cross_cx, cross_cy - row_h)

        # Carta 6 (futuro, derecha)
        paste_with_label(5, cross_cx + col_w, cross_cy)

        # Columna derecha (staff): 7, 8, 9, 10 de abajo a arriba
        for i, card_idx in enumerate([6, 7, 8, 9]):
            sy = canvas_h - gap - (i + 1) * (ch_s + gap + label_h)
            paste_with_label(card_idx, staff_x, sy)

        return compose_to_jpeg(canvas)
    except Exception as e:
        logger.error(f"Error composing celtic cross: {e}")
        return None


def compose_two_rows(cards: list[dict], top_count: int) -> BytesIO | None:
    """Composicion generica en 2 filas (top_count arriba, resto abajo centrado)."""
    try:
        images = []
        for card in cards:
            img = load_card_image(card["id"])
            if card["inverted"]:
                img = invert_card_image(img)
            images.append(img)

        cw, ch = images[0].size
        # Escalar si hay muchas cartas
        if top_count >= 4:
            target_w = 200
            scale = target_w / cw
            cw_s, ch_s = target_w, int(ch * scale)
            images = [img.resize((cw_s, ch_s), Image.LANCZOS) for img in images]
        else:
            cw_s, ch_s = cw, ch

        gap = 20
        padding = 30
        label_h = 40
        font = _get_label_font(18)

        bottom_count = len(cards) - top_count
        max_cols = max(top_count, bottom_count)
        canvas_w = max_cols * cw_s + (max_cols - 1) * gap + padding * 2
        canvas_h = ch_s * 2 + gap + padding * 2 + label_h * 2

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(25, 20, 30))
        draw = ImageDraw.Draw(canvas)

        def draw_card(idx, x, y):
            canvas.paste(images[idx], (x, y))
            label = cards[idx].get("position", f"Carta {idx+1}")
            if cards[idx]["inverted"]:
                label += " ↓"
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            lx = x + (cw_s - tw) // 2
            draw.text((lx, y + ch_s + 5), label, fill=(200, 185, 150), font=font)

        # Fila superior (centrada)
        top_w = top_count * cw_s + (top_count - 1) * gap
        top_offset = (canvas_w - top_w) // 2
        for i in range(top_count):
            x = top_offset + i * (cw_s + gap)
            draw_card(i, x, padding)

        # Fila inferior (centrada)
        bot_w = bottom_count * cw_s + (bottom_count - 1) * gap
        bot_offset = (canvas_w - bot_w) // 2
        y2 = padding + ch_s + label_h + gap
        for i in range(bottom_count):
            x = bot_offset + i * (cw_s + gap)
            draw_card(top_count + i, x, y2)

        return compose_to_jpeg(canvas)
    except Exception as e:
        logger.error(f"Error composing two rows: {e}")
        return None


def compose_herradura(cards: list[dict]) -> BytesIO | None:
    """Herradura: 7 cartas en 2 filas (4+3)."""
    return compose_two_rows(cards, top_count=4)


def compose_relacion(cards: list[dict]) -> BytesIO | None:
    """Relacion: 6 cartas en 2 filas (3+3)."""
    return compose_two_rows(cards, top_count=3)


def compose_estrella(cards: list[dict]) -> BytesIO | None:
    """Estrella: 7 cartas — 3 arriba, 1 centro, 3 abajo (hexagrama con sintesis)."""
    return compose_two_rows(cards, top_count=4)  # 4+3 como herradura


def compose_cruz_simple(cards: list[dict]) -> BytesIO | None:
    """Cruz simple: 5 cartas en forma de cruz.

    Layout:
              [4]
        [2]  [1]  [3]
              [5]
    """
    try:
        if len(cards) < 5:
            return None

        images = []
        for card in cards:
            img = load_card_image(card["id"])
            if card["inverted"]:
                img = invert_card_image(img)
            images.append(img)

        cw, ch = images[0].size
        target_w = 220
        scale = target_w / cw
        cw_s, ch_s = target_w, int(ch * scale)
        images = [img.resize((cw_s, ch_s), Image.LANCZOS) for img in images]

        gap = 15
        label_h = 30
        font = _get_label_font(16)
        cell_w = cw_s + gap
        cell_h = ch_s + gap + label_h

        canvas_w = cell_w * 3 + gap
        canvas_h = cell_h * 3 + gap

        canvas = Image.new("RGB", (canvas_w, canvas_h), color=(25, 20, 30))
        draw = ImageDraw.Draw(canvas)

        def draw_card(idx, col, row):
            x = gap + col * cell_w
            y = gap + row * cell_h
            canvas.paste(images[idx], (x, y))
            label = cards[idx].get("position", f"{idx+1}")
            if cards[idx]["inverted"]:
                label += " ↓"
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            lx = x + (cw_s - tw) // 2
            draw.text((lx, y + ch_s + 3), label, fill=(200, 185, 150), font=font)

        # Posiciones: 1=centro, 2=izq, 3=der, 4=arriba, 5=abajo
        draw_card(0, 1, 1)  # Centro
        draw_card(1, 0, 1)  # Izquierda (Pasado)
        draw_card(2, 2, 1)  # Derecha (Futuro)
        draw_card(3, 1, 0)  # Arriba (Consciente)
        draw_card(4, 1, 2)  # Abajo (Inconsciente)

        return compose_to_jpeg(canvas)
    except Exception as e:
        logger.error(f"Error composing cruz simple: {e}")
        return None


def compose_tarot(variant: str, cards: list[dict]) -> BytesIO | None:
    """Dispatcher de composiciones segun variante."""
    dispatchers = {
        "1_carta": compose_single,
        "3_cartas": compose_three,
        "cruz_celta": compose_celtic_cross,
        "herradura": compose_herradura,
        "relacion": compose_relacion,
        "estrella": compose_estrella,
        "cruz_simple": compose_cruz_simple,
        "si_no": compose_three,       # 3 cartas horizontal, mismo layout
        "tirada_dia": compose_single,  # 1 carta, mismo layout
    }
    composer = dispatchers.get(variant)
    if composer:
        return composer(cards)
    return None


def build_caption(variant: str, cards: list[dict]) -> str:
    """Construye caption descriptivo para la imagen."""
    lines = []
    for card in cards:
        label = card.get("position", "")
        name = card["name"]
        inv = " (invertida)" if card["inverted"] else ""
        if label:
            lines.append(f"{label}: {name}{inv}")
        else:
            lines.append(f"{name}{inv}")
    return "\n".join(lines)


def build_text_fallback(variant: str, cards: list[dict]) -> str:
    """Texto descriptivo si la composición de imagen falla."""
    lines = ["🃏 Tu tirada:"]
    for card in cards:
        label = card.get("position", "")
        name = card["name"]
        inv = " ↓" if card["inverted"] else ""
        if label:
            lines.append(f"  {label}: {name}{inv}")
        else:
            lines.append(f"  {name}{inv}")
    return "\n".join(lines)
