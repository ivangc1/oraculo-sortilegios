"""Tests de geomancia: generador, escudo, XOR, 3+ escudos calculados a mano.

XOR geomántico: por cada fila, iguales→2 (par), distintos→1 (impar).
"""

from PIL import Image

from generators.geomancia import (
    build_drawn_data_shield,
    generate_figure,
    generate_shield,
    get_all_figures,
    lookup_figure,
    xor_figures,
)
from images.geomancy_renderer import render_shield, render_single_figure


# === Datos ===

def test_16_figures():
    figs = get_all_figures()
    assert len(figs) == 16


def test_all_figures_have_4_rows():
    for fig in get_all_figures():
        assert len(fig["points"]) == 4
        for p in fig["points"]:
            assert p in (1, 2)


def test_all_figure_patterns_unique():
    figs = get_all_figures()
    patterns = [tuple(f["points"]) for f in figs]
    assert len(patterns) == len(set(patterns)), "Hay patrones duplicados"


def test_lookup_via():
    fig = lookup_figure([1, 1, 1, 1])
    assert fig["name"] == "Via"


def test_lookup_populus():
    fig = lookup_figure([2, 2, 2, 2])
    assert fig["name"] == "Populus"


# === XOR geomántico ===

def test_xor_same():
    """Iguales → 2 (par)."""
    assert xor_figures([1, 1, 1, 1], [1, 1, 1, 1]) == [2, 2, 2, 2]
    assert xor_figures([2, 2, 2, 2], [2, 2, 2, 2]) == [2, 2, 2, 2]


def test_xor_different():
    """Distintos → 1 (impar)."""
    assert xor_figures([1, 1, 1, 1], [2, 2, 2, 2]) == [1, 1, 1, 1]


def test_xor_mixed():
    assert xor_figures([1, 2, 1, 2], [1, 1, 2, 2]) == [2, 1, 1, 2]
    # 1+1=2(par)→2, 2+1=3(impar)→1, 1+2=3(impar)→1, 2+2=4(par)→2


def test_xor_commutative():
    a = [1, 2, 1, 2]
    b = [2, 1, 2, 1]
    assert xor_figures(a, b) == xor_figures(b, a)


# === Escudo calculado a mano — Test 1 ===

def test_shield_hand_calculated_1():
    """Escudo con madres fijas, verificado fila por fila.

    Madres:
      M1=[1,1,2,2] (Fortuna Major)
      M2=[2,2,1,1] (Fortuna Minor)
      M3=[1,1,1,1] (Via)
      M4=[2,2,2,2] (Populus)

    Hijas (transpuestas):
      H1=[fila0: M1[0],M2[0],M3[0],M4[0]] = [1,2,1,2] (Rubeus)
      H2=[fila1: M1[1],M2[1],M3[1],M4[1]] = [1,2,1,2] (Rubeus)
      H3=[fila2: M1[2],M2[2],M3[2],M4[2]] = [2,1,1,2] (Albus)
      H4=[fila3: M1[3],M2[3],M3[3],M4[3]] = [2,1,1,2] (Albus)

    Sobrinas (XOR):
      S1 = M1 ⊕ M2 = [1+2,1+2,2+1,2+1] = [1,1,1,1] (Via)
      S2 = M3 ⊕ M4 = [1+2,1+2,1+2,1+2] = [1,1,1,1] (Via)
      S3 = H1 ⊕ H2 = [1+1,2+2,1+1,2+2] = [2,2,2,2] (Populus)
      S4 = H3 ⊕ H4 = [2+2,1+1,1+1,2+2] = [2,2,2,2] (Populus)

    Testigos:
      TD = S1 ⊕ S2 = [1+1,1+1,1+1,1+1] = [2,2,2,2] (Populus)
      TI = S3 ⊕ S4 = [2+2,2+2,2+2,2+2] = [2,2,2,2] (Populus)

    Juez:
      J = TD ⊕ TI = [2+2,2+2,2+2,2+2] = [2,2,2,2] (Populus)

    Reconciliador:
      R = J ⊕ M1 = [2+1,2+1,2+2,2+2] = [1,1,2,2] (Fortuna Major)
    """
    m1, m2, m3, m4 = [1,1,2,2], [2,2,1,1], [1,1,1,1], [2,2,2,2]

    # Hijas
    h1 = [m1[0], m2[0], m3[0], m4[0]]
    assert h1 == [1, 2, 1, 2]
    h2 = [m1[1], m2[1], m3[1], m4[1]]
    assert h2 == [1, 2, 1, 2]
    h3 = [m1[2], m2[2], m3[2], m4[2]]
    assert h3 == [2, 1, 1, 2]
    h4 = [m1[3], m2[3], m3[3], m4[3]]
    assert h4 == [2, 1, 1, 2]

    # Sobrinas
    s1 = xor_figures(m1, m2)
    assert s1 == [1, 1, 1, 1], f"S1={s1}"
    s2 = xor_figures(m3, m4)
    assert s2 == [1, 1, 1, 1], f"S2={s2}"
    s3 = xor_figures(h1, h2)
    assert s3 == [2, 2, 2, 2], f"S3={s3}"
    s4 = xor_figures(h3, h4)
    assert s4 == [2, 2, 2, 2], f"S4={s4}"

    # Testigos
    td = xor_figures(s1, s2)
    assert td == [2, 2, 2, 2], f"TD={td}"
    ti = xor_figures(s3, s4)
    assert ti == [2, 2, 2, 2], f"TI={ti}"

    # Juez
    j = xor_figures(td, ti)
    assert j == [2, 2, 2, 2], f"J={j}"

    # Reconciliador
    r = xor_figures(j, m1)
    assert r == [1, 1, 2, 2], f"R={r}"

    # Verificar nombres
    assert lookup_figure(s1)["name"] == "Via"
    assert lookup_figure(j)["name"] == "Populus"
    assert lookup_figure(r)["name"] == "Fortuna Major"


# === Escudo calculado a mano — Test 2 ===

def test_shield_hand_calculated_2():
    """Segundo escudo con madres diferentes.

    Madres:
      M1=[2,1,2,1] (Puer)
      M2=[1,2,1,2] (Rubeus)
      M3=[2,1,1,1] (Caput Draconis)
      M4=[1,2,2,2] (Cauda Draconis)

    Hijas:
      H1=[M1[0],M2[0],M3[0],M4[0]] = [2,1,2,1] (Puer)
      H2=[M1[1],M2[1],M3[1],M4[1]] = [1,2,1,2] (Rubeus)
      H3=[M1[2],M2[2],M3[2],M4[2]] = [2,1,1,2] (Albus)
      H4=[M1[3],M2[3],M3[3],M4[3]] = [1,2,1,2] (Rubeus)

    Sobrinas:
      S1 = M1⊕M2 = [2+1,1+2,2+1,1+2] = [1,1,1,1] (Via)
      S2 = M3⊕M4 = [2+1,1+2,1+2,1+2] = [1,1,1,1] (Via)
      S3 = H1⊕H2 = [2+1,1+2,2+1,1+2] = [1,1,1,1] (Via)
      S4 = H3⊕H4 = [2+1,1+2,1+1,2+2] = [1,1,2,2] (Fortuna Major)

    Testigos:
      TD = S1⊕S2 = [1+1,1+1,1+1,1+1] = [2,2,2,2] (Populus)
      TI = S3⊕S4 = [1+1,1+1,1+2,1+2] = [2,2,1,1] (Fortuna Minor)

    Juez:
      J = TD⊕TI = [2+2,2+2,2+1,2+1] = [2,2,1,1] (Fortuna Minor)

    Reconciliador:
      R = J⊕M1 = [2+2,2+1,1+2,1+1] = [2,1,1,2] (Albus)
    """
    m1, m2 = [2,1,2,1], [1,2,1,2]
    m3, m4 = [2,1,1,1], [1,2,2,2]

    s1 = xor_figures(m1, m2)
    assert s1 == [1, 1, 1, 1]
    s2 = xor_figures(m3, m4)
    assert s2 == [1, 1, 1, 1]

    h1 = [m1[0], m2[0], m3[0], m4[0]]
    h2 = [m1[1], m2[1], m3[1], m4[1]]
    h3 = [m1[2], m2[2], m3[2], m4[2]]
    h4 = [m1[3], m2[3], m3[3], m4[3]]
    assert h1 == [2, 1, 2, 1]
    assert h3 == [2, 1, 1, 2]

    s3 = xor_figures(h1, h2)
    assert s3 == [1, 1, 1, 1]
    s4 = xor_figures(h3, h4)
    assert s4 == [1, 1, 2, 2]

    td = xor_figures(s1, s2)
    assert td == [2, 2, 2, 2]
    ti = xor_figures(s3, s4)
    assert ti == [2, 2, 1, 1]

    j = xor_figures(td, ti)
    assert j == [2, 2, 1, 1]
    assert lookup_figure(j)["name"] == "Fortuna Minor"

    r = xor_figures(j, m1)
    assert r == [2, 1, 1, 2]
    assert lookup_figure(r)["name"] == "Albus"


# === Escudo calculado a mano — Test 3 ===

def test_shield_hand_calculated_3():
    """Tercer escudo: todas las madres iguales.

    Madres: M1=M2=M3=M4=[1,2,1,2] (Rubeus)

    Hijas: todas [1,1,1,1] → no! transpuesta de 4 copias de [1,2,1,2]:
      H1=[1,1,1,1] (Via)
      H2=[2,2,2,2] (Populus)
      H3=[1,1,1,1] (Via)
      H4=[2,2,2,2] (Populus)

    Sobrinas:
      S1 = M1⊕M2 = [1+1,2+2,1+1,2+2] = [2,2,2,2] (Populus)
      S2 = M3⊕M4 = [2,2,2,2] (Populus)
      S3 = H1⊕H2 = [1+2,1+2,1+2,1+2] = [1,1,1,1] (Via)
      S4 = H3⊕H4 = [1+2,1+2,1+2,1+2] = [1,1,1,1] (Via)

    Testigos:
      TD = S1⊕S2 = [2,2,2,2] (Populus)
      TI = S3⊕S4 = [2,2,2,2] (Populus)

    Juez = [2,2,2,2] (Populus)
    Reconciliador = J⊕M1 = [2+1,2+2,2+1,2+2] = [1,2,1,2] (Rubeus)
    """
    m = [1, 2, 1, 2]

    h1 = [m[0], m[0], m[0], m[0]]
    assert h1 == [1, 1, 1, 1]
    h2 = [m[1], m[1], m[1], m[1]]
    assert h2 == [2, 2, 2, 2]

    s1 = xor_figures(m, m)
    assert s1 == [2, 2, 2, 2]

    s3 = xor_figures(h1, h2)
    assert s3 == [1, 1, 1, 1]

    td = xor_figures(s1, s1)
    assert td == [2, 2, 2, 2]
    ti = xor_figures(s3, s3)
    assert ti == [2, 2, 2, 2]

    j = xor_figures(td, ti)
    assert j == [2, 2, 2, 2]
    assert lookup_figure(j)["name"] == "Populus"

    r = xor_figures(j, m)
    assert r == [1, 2, 1, 2]
    assert lookup_figure(r)["name"] == "Rubeus"


# === Generador ===

def test_generate_figure_valid():
    for _ in range(50):
        fig = generate_figure()
        assert len(fig["points"]) == 4
        assert all(p in (1, 2) for p in fig["points"])
        assert "name" in fig


def test_generate_shield_structure():
    shield = generate_shield()
    assert len(shield["mothers"]) == 4
    assert len(shield["daughters"]) == 4
    assert len(shield["nieces"]) == 4
    assert len(shield["witnesses"]) == 2
    assert "judge" in shield
    assert "reconciler" in shield


def test_generate_shield_daughters_are_transpose():
    """Las hijas son la transposición de las madres."""
    shield = generate_shield()
    for i in range(4):
        for j in range(4):
            assert shield["daughters"][i]["points"][j] == shield["mothers"][j]["points"][i]


def test_generate_shield_nieces_are_xor():
    """Las sobrinas son XOR de los pares correctos."""
    shield = generate_shield()
    m = shield["mothers"]
    d = shield["daughters"]
    n = shield["nieces"]
    assert n[0]["points"] == xor_figures(m[0]["points"], m[1]["points"])
    assert n[1]["points"] == xor_figures(m[2]["points"], m[3]["points"])
    assert n[2]["points"] == xor_figures(d[0]["points"], d[1]["points"])
    assert n[3]["points"] == xor_figures(d[2]["points"], d[3]["points"])


def test_generate_shield_judge_is_xor_witnesses():
    shield = generate_shield()
    w = shield["witnesses"]
    expected = xor_figures(w[0]["points"], w[1]["points"])
    assert shield["judge"]["points"] == expected


def test_drawn_data_shield_count():
    shield = generate_shield()
    data = build_drawn_data_shield(shield)
    # 4+4+4+2+1+1 = 16 entries
    assert len(data["figures"]) == 16


# === Renderer ===

def test_render_single_figure():
    fig = generate_figure()
    buf = render_single_figure(fig)
    assert buf is not None
    img = Image.open(buf)
    assert img.format == "JPEG"
    buf.close()


def test_render_shield():
    shield = generate_shield()
    buf = render_shield(shield)
    assert buf is not None
    img = Image.open(buf)
    assert img.format == "JPEG"
    buf.close()
