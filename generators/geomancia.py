"""Generador de figuras y escudo geomántico completo.

Escudo completo:
  4 Madres (generadas aleatoriamente, SystemRandom.choice([1,2]) × 4 filas)
  4 Hijas (transpuestas de las Madres: fila i de hija j = fila j de madre i)
  4 Sobrinas (XOR par a par: sobrina1 = madre1 ⊕ madre2, etc.)
  2 Testigos (XOR de Sobrinas par a par)
  1 Juez (XOR de los 2 Testigos)
  1 Reconciliador (XOR Juez + Primera Madre, si el juez es ambiguo)

XOR geomántico: por cada fila, si son iguales → 2 (par), si son distintos → 1 (impar).
"""

import json
import random
from pathlib import Path

_rng = random.SystemRandom()

_FIGURES_DATA: list[dict] | None = None
_POINTS_TO_FIGURE: dict[str, dict] | None = None


def _load_figures() -> None:
    global _FIGURES_DATA, _POINTS_TO_FIGURE
    if _FIGURES_DATA is not None:
        return
    path = Path(__file__).parent.parent / "data" / "geomancia_figuras.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _FIGURES_DATA = data["figures"]
    _POINTS_TO_FIGURE = {}
    for fig in _FIGURES_DATA:
        key = "".join(str(p) for p in fig["points"])
        _POINTS_TO_FIGURE[key] = fig


def get_all_figures() -> list[dict]:
    _load_figures()
    return _FIGURES_DATA


def lookup_figure(points: list[int]) -> dict:
    """Busca figura por patrón de puntos [1|2, 1|2, 1|2, 1|2]."""
    _load_figures()
    key = "".join(str(p) for p in points)
    fig = _POINTS_TO_FIGURE.get(key)
    if fig is None:
        return {"points": points, "name": "Desconocida", "spanish": "Desconocida",
                "element": "?", "planet": "?"}
    return fig.copy()


def xor_figures(a: list[int], b: list[int]) -> list[int]:
    """XOR geomántico: iguales→2 (par), distintos→1 (impar)."""
    result = []
    for pa, pb in zip(a, b):
        total = pa + pb
        result.append(2 if total % 2 == 0 else 1)
    return result


def generate_figure() -> dict:
    """Genera una sola figura geomántica aleatoria."""
    _load_figures()
    points = [_rng.choice([1, 2]) for _ in range(4)]
    fig = lookup_figure(points)
    return fig


def generate_shield() -> dict:
    """Genera escudo geomántico completo.

    Returns:
        dict con mothers, daughters, nieces, witnesses, judge, reconciler.
        Cada elemento tiene: points, name, spanish, position.
    """
    _load_figures()

    # 4 Madres (generadas aleatoriamente)
    mothers = []
    for i in range(4):
        points = [_rng.choice([1, 2]) for _ in range(4)]
        fig = lookup_figure(points)
        fig["position"] = f"Madre {i + 1}"
        mothers.append(fig)

    # 4 Hijas (transpuestas: fila i de hija j = fila j de madre i)
    daughters = []
    for i in range(4):
        points = [mothers[j]["points"][i] for j in range(4)]
        fig = lookup_figure(points)
        fig["position"] = f"Hija {i + 1}"
        daughters.append(fig)

    # 4 Sobrinas (XOR par a par)
    nieces = []
    pairs = [(mothers[0], mothers[1]), (mothers[2], mothers[3]),
             (daughters[0], daughters[1]), (daughters[2], daughters[3])]
    for i, (a, b) in enumerate(pairs):
        points = xor_figures(a["points"], b["points"])
        fig = lookup_figure(points)
        fig["position"] = f"Sobrina {i + 1}"
        nieces.append(fig)

    # 2 Testigos (XOR de Sobrinas par a par)
    witness_right_points = xor_figures(nieces[0]["points"], nieces[1]["points"])
    witness_right = lookup_figure(witness_right_points)
    witness_right["position"] = "Testigo Derecho"

    witness_left_points = xor_figures(nieces[2]["points"], nieces[3]["points"])
    witness_left = lookup_figure(witness_left_points)
    witness_left["position"] = "Testigo Izquierdo"

    witnesses = [witness_right, witness_left]

    # 1 Juez (XOR de los 2 Testigos)
    judge_points = xor_figures(witness_right["points"], witness_left["points"])
    judge = lookup_figure(judge_points)
    judge["position"] = "Juez"

    # Reconciliador (XOR Juez + Primera Madre)
    reconciler_points = xor_figures(judge["points"], mothers[0]["points"])
    reconciler = lookup_figure(reconciler_points)
    reconciler["position"] = "Reconciliador"

    return {
        "mothers": mothers,
        "daughters": daughters,
        "nieces": nieces,
        "witnesses": witnesses,
        "judge": judge,
        "reconciler": reconciler,
    }


def build_drawn_data_single(figure: dict) -> dict:
    return {
        "figures": [
            {"name": figure["name"], "points": figure["points"], "position": "figura_1"}
        ]
    }


def build_drawn_data_shield(shield: dict) -> dict:
    figures = []
    for group_key in ("mothers", "daughters", "nieces", "witnesses"):
        for fig in shield[group_key]:
            figures.append({
                "name": fig["name"],
                "points": fig["points"],
                "position": fig["position"],
            })
    figures.append({
        "name": shield["judge"]["name"],
        "points": shield["judge"]["points"],
        "position": "Juez",
    })
    figures.append({
        "name": shield["reconciler"]["name"],
        "points": shield["reconciler"]["points"],
        "position": "Reconciliador",
    })
    return {"figures": figures}
