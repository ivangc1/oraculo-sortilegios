"""Compone los 72 sigilos canónicos sobre los retratos normalizados.

Fuentes:
    assets/goetia_portraits/NN.png   (retratos normalizados 1024x1536)
    assets/goetia_sigils/NN.png      (sigilos 450x450, negro sobre blanco)

Destino:
    assets/goetia_cards/NN.png       (retratos con sigilo en esquina superior derecha)

Estrategia:
- El sigilo se coloca en la esquina SUPERIOR DERECHA (fidelidad al estilo
  del Dictionnaire Infernal, donde el sello ornamenta la lámina).
- Tamaño del sigilo: 16% del ancho del retrato (≈164px sobre 1024).
- Se usa blending multiply: los trazos negros del sigilo quedan sobre el
  pergamino, los blancos se funden con la textura del fondo.
- Margen desde los bordes: ≈3% del ancho (≈30px).

Uso:
    python scripts/compose_goetia_cards.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPT_DIR = Path(__file__).parent
REPO_ROOT = SCRIPT_DIR.parent

PORTRAITS_DIR = REPO_ROOT / "assets" / "goetia_portraits"
SIGILS_DIR = REPO_ROOT / "assets" / "goetia_sigils"
OUT_DIR = REPO_ROOT / "assets" / "goetia_cards"

SIGIL_SIZE_FRAC = 0.16    # 16% del ancho del retrato
MARGIN_FRAC = 0.025       # 2.5% del ancho desde el borde


def multiply_sigil_onto(portrait: Image.Image, sigil: Image.Image) -> Image.Image:
    """Compone el sigilo sobre el retrato en esquina superior derecha (multiply)."""
    W, H = portrait.size
    size = int(W * SIGIL_SIZE_FRAC)
    margin = int(W * MARGIN_FRAC)

    # Redimensionar sigilo manteniendo cuadrado
    sigil_rgb = sigil.convert("RGB").resize((size, size), Image.LANCZOS)

    # Posición: esquina superior derecha
    x = W - size - margin
    y = margin

    # Región del retrato donde va el sigilo
    roi = portrait.crop((x, y, x + size, y + size)).convert("RGB")

    # Blend multiply: roi * sigil / 255
    roi_arr = np.array(roi, dtype=np.float32)
    sig_arr = np.array(sigil_rgb, dtype=np.float32) / 255.0
    out = roi_arr * sig_arr
    out = np.clip(out, 0, 255).astype(np.uint8)
    blended = Image.fromarray(out)

    # Pegar de vuelta
    result = portrait.copy()
    result.paste(blended, (x, y))
    return result


def main() -> int:
    if not PORTRAITS_DIR.is_dir():
        print(f"ERROR: {PORTRAITS_DIR} no existe. Ejecuta normalize_goetia_portraits.py primero.")
        return 1
    if not SIGILS_DIR.is_dir():
        print(f"ERROR: {SIGILS_DIR} no existe. Ejecuta download_sigils.py primero.")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ok = 0
    errors: list[str] = []
    for num in range(1, 73):
        portrait_path = PORTRAITS_DIR / f"{num:02d}.png"
        sigil_path = SIGILS_DIR / f"{num:02d}.png"
        out_path = OUT_DIR / f"{num:02d}.png"

        if not portrait_path.exists():
            errors.append(f"{num:02d} falta retrato")
            continue
        if not sigil_path.exists():
            errors.append(f"{num:02d} falta sigilo")
            continue

        try:
            portrait = Image.open(portrait_path).convert("RGB")
            sigil = Image.open(sigil_path)
            card = multiply_sigil_onto(portrait, sigil)
            card.save(out_path, "PNG", optimize=True)
            ok += 1
            if num <= 3 or num in (20, 45, 72):
                print(f"  {num:02d} compuesto -> {out_path.name}")
        except Exception as e:
            errors.append(f"{num:02d}: {e}")

    print("=" * 60)
    print(f"Total: {ok}/72 compuestos")
    if errors:
        print(f"Errores ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        return 1
    print(f"\nCartas Goetia en {OUT_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
