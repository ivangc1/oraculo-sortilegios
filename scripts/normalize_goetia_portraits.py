"""Normaliza los 72 retratos Goetia a un formato unificado.

Fuentes:
    A) Le Breton auténticos (36)  -> assets/goetia_portraits_lebreton/NN_Nombre.{jpg,png}
    B) IA regeneradas (42)        -> C:\\Users\\ivang\\Downloads\\demoniosfinal\\cleaned_py\\NN_Nombre.png

Destino:
    assets/goetia_portraits/NN.png   (solo número, 1024x1536, 2:3 vertical, sepia uniforme)

Reglas:
- Si un número tiene versión Le Breton, se usa ESA (prioridad auténtica).
- Si no, se usa la IA.
- Las Le Breton (blanco sobre blanco) se tiñen con sepia objetivo para casar con las IA.
- Todas se recortan/rellenan a 1024x1536 (2:3 vertical).
- Salida: PNG optimizado.

Uso:
    python scripts/normalize_goetia_portraits.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from PIL import Image

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy requerido. pip install numpy")
    sys.exit(1)

# --- Configuración ---
SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent

LEBRETON_DIR = REPO_ROOT / "assets" / "goetia_portraits_lebreton"
IA_DIR = Path(r"C:\Users\ivang\Downloads\demoniosfinal\cleaned_py")
OUT_DIR = REPO_ROOT / "assets" / "goetia_portraits"

TARGET_SIZE = (1024, 1536)  # ancho x alto, 2:3 vertical
TARGET_ASPECT = TARGET_SIZE[0] / TARGET_SIZE[1]  # 0.6667

# Color sepia objetivo (sampleado del pergamino de las IA)
SEPIA_COLOR = (232, 218, 188)  # parchment crema cálido

# Imagen IA de referencia para extraer textura de pergamino
# (bordes mottled, envejecidos — se aplicarán a los Le Breton)
TEXTURE_SOURCE_IA = "03_Vassago.png"


def collect_sources() -> dict[int, tuple[Path, str]]:
    """Retorna {numero -> (ruta, fuente)} priorizando Le Breton sobre IA."""
    sources: dict[int, tuple[Path, str]] = {}

    # Primero IA (baseline)
    if IA_DIR.is_dir():
        for p in sorted(IA_DIR.iterdir()):
            if p.suffix.lower() != ".png":
                continue
            stem = p.stem  # NN_Nombre
            if len(stem) >= 2 and stem[:2].isdigit():
                num = int(stem[:2])
                if 1 <= num <= 72:
                    sources[num] = (p, "IA")

    # Luego Le Breton (sobrescribe IA si hay)
    if LEBRETON_DIR.is_dir():
        for p in sorted(LEBRETON_DIR.iterdir()):
            if p.suffix.lower() not in (".jpg", ".jpeg", ".png"):
                continue
            stem = p.stem
            if len(stem) >= 2 and stem[:2].isdigit():
                num = int(stem[:2])
                if 1 <= num <= 72:
                    sources[num] = (p, "LeBreton")

    return sources


def apply_sepia_tint(img: Image.Image, target_sepia: tuple[int, int, int]) -> Image.Image:
    """Tiñe una imagen (blanco sobre blanco) con sepia objetivo.

    Multiplica los canales por factores tal que blanco (255,255,255) se
    convierte en el sepia objetivo y negro (0,0,0) se queda en negro.
    """
    arr = np.array(img.convert("RGB"), dtype=np.float32)
    factors = np.array(target_sepia, dtype=np.float32) / 255.0
    out = arr * factors
    out = np.clip(out, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


def build_parchment_canvas(texture_src: Path, size: tuple[int, int]) -> Image.Image:
    """Construye un lienzo de pergamino envejecido a tamaño objetivo.

    Estrategia: toma la imagen IA de referencia, la redimensiona a `size`
    y usa SOLO sus píxeles de fondo (reemplazando el grabado por
    interpolación de bordes). Como atajo, escala la imagen completa
    y luego APLICA UN DESENFOQUE MUY FUERTE para borrar el grabado
    dejando solo la textura de pergamino y sus manchas.
    """
    from PIL import ImageFilter

    src = Image.open(texture_src).convert("RGB")
    # Escalar a tamaño objetivo
    canvas = src.resize(size, Image.LANCZOS)
    # Desenfocar fuerte para borrar el grabado conservando la textura
    canvas = canvas.filter(ImageFilter.GaussianBlur(radius=80))
    # Sutileza: boostear contraste de la textura para que las manchas
    # del pergamino se noten
    arr = np.array(canvas, dtype=np.float32)
    # Centrar en 232,218,188 y subir variación 1.3x
    mean = np.array(SEPIA_COLOR, dtype=np.float32)
    arr = mean + (arr - mean) * 1.3
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def multiply_blend(fg: Image.Image, bg: Image.Image) -> Image.Image:
    """Blend 'multiply': bg * fg / 255. Blancos de fg dejan ver bg, negros persisten."""
    fg_arr = np.array(fg.convert("RGB"), dtype=np.float32) / 255.0
    bg_arr = np.array(bg.convert("RGB"), dtype=np.float32)
    out = bg_arr * fg_arr
    out = np.clip(out, 0, 255).astype(np.uint8)
    return Image.fromarray(out)


def is_mostly_white(img: Image.Image, threshold: int = 230) -> bool:
    """Detecta si la imagen tiene fondo blanco (Le Breton) o sepia (IA)."""
    arr = np.array(img.convert("RGB"))
    h, w = arr.shape[:2]
    # Samplea esquinas (fondo)
    corners = np.concatenate([
        arr[:h//10, :w//10].reshape(-1, 3),
        arr[:h//10, -w//10:].reshape(-1, 3),
        arr[-h//10:, :w//10].reshape(-1, 3),
        arr[-h//10:, -w//10:].reshape(-1, 3),
    ])
    mean_brightness = corners.mean()
    return mean_brightness > threshold


def pad_to_aspect(
    img: Image.Image, aspect: float, fill: tuple[int, int, int]
) -> Image.Image:
    """Padea imagen a aspect ratio objetivo con color fill."""
    w, h = img.size
    cur_aspect = w / h
    if abs(cur_aspect - aspect) < 0.005:
        return img
    if cur_aspect > aspect:
        # Demasiado ancha: añadir pad vertical
        new_h = int(round(w / aspect))
        top = (new_h - h) // 2
        out = Image.new("RGB", (w, new_h), fill)
        out.paste(img, (0, top))
    else:
        # Demasiado alta: añadir pad horizontal
        new_w = int(round(h * aspect))
        left = (new_w - w) // 2
        out = Image.new("RGB", (new_w, h), fill)
        out.paste(img, (left, 0))
    return out


def normalize_image(
    src: Path,
    source_type: str,
    parchment_canvas: Optional[Image.Image] = None,
) -> Image.Image:
    """Carga, aplica textura de pergamino (si Le Breton) y normaliza tamaño."""
    img = Image.open(src).convert("RGB")

    if source_type == "LeBreton" or is_mostly_white(img):
        # Le Breton: fondo blanco -> pad a 2:3 con blanco, resize a target,
        # multiply con lienzo de pergamino texturado
        img = pad_to_aspect(img, TARGET_ASPECT, (255, 255, 255))
        img = img.resize(TARGET_SIZE, Image.LANCZOS)
        if parchment_canvas is not None:
            img = multiply_blend(img, parchment_canvas)
        else:
            img = apply_sepia_tint(img, SEPIA_COLOR)
    else:
        # IA: ya tiene pergamino envejecido, solo pad+resize
        img = pad_to_aspect(img, TARGET_ASPECT, SEPIA_COLOR)
        img = img.resize(TARGET_SIZE, Image.LANCZOS)

    return img


def main() -> int:
    sources = collect_sources()
    print(f"Fuentes recogidas: {len(sources)}/72")

    missing = sorted(set(range(1, 73)) - set(sources.keys()))
    if missing:
        print(f"FALTAN: {missing}")

    if not sources:
        print("ERROR: sin fuentes. Comprueba rutas.")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Construir lienzo de pergamino desde una IA de referencia
    texture_src = IA_DIR / TEXTURE_SOURCE_IA
    parchment_canvas = None
    if texture_src.exists():
        print(f"Construyendo lienzo de pergamino desde {texture_src.name}...")
        parchment_canvas = build_parchment_canvas(texture_src, TARGET_SIZE)
    else:
        print(f"AVISO: no se encontró {texture_src}, Le Breton con sepia plano.")

    by_type = {"LeBreton": 0, "IA": 0}
    errors: list[str] = []

    for num in sorted(sources.keys()):
        src, stype = sources[num]
        try:
            img = normalize_image(src, stype, parchment_canvas)
            out = OUT_DIR / f"{num:02d}.png"
            img.save(out, "PNG", optimize=True)
            by_type[stype] += 1
            print(f"  {num:02d} [{stype:>8}] {src.name} -> {out.name}")
        except Exception as e:
            errors.append(f"{num:02d} {src.name}: {e}")
            print(f"  {num:02d} ERROR: {e}")

    print("=" * 60)
    print(f"Total: {sum(by_type.values())}/72")
    print(f"  Le Breton auténticos: {by_type['LeBreton']}")
    print(f"  IA regeneradas:       {by_type['IA']}")
    if errors:
        print(f"Errores ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        return 1
    print(f"\nRetratos normalizados en {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
