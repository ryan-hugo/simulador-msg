"""ETAPA 6 - Validação matemática (testes automáticos).

Execute no terminal:  python -m pytest -v

Cada teste compara o resultado do programa com um valor calculado à mão
nos Capítulos 4 e 5. pytest.approx tolera diferenças de arredondamento
da ordem de 1e-9, o que é suficiente para cálculos em ponto flutuante.
"""

from dataclasses import replace

import pytest

from simulador.parametros import ParametrosProcesso
from simulador.simulacao import RENDIMENTOS_CENARIOS, simular, simular_cenarios

REF = ParametrosProcesso()  # condição de referência


# ---------- Capítulo 4: Tabela 6 (vazões, kg/h) ----------
TABELA_6 = {
    "01": {"Água": 3200, "Açúcar": 800, "MSG": 0, "Outros produtos": 0},
    "02": {"Água": 3200, "Açúcar": 160, "MSG": 320, "Outros produtos": 320},
    "03": {"Água": 3200, "Açúcar": 160, "MSG": 320, "Outros produtos": 320},
    "04": {"Água": 0, "Açúcar": 0, "MSG": 288, "Outros produtos": 0},
    "05": {"Água": 3200, "Açúcar": 160, "MSG": 32, "Outros produtos": 320},
}
TOTAIS = {"01": 4000, "02": 4000, "03": 4000, "04": 288, "05": 3712}


@pytest.mark.parametrize("corrente", TABELA_6)
def test_vazoes_tabela_6(corrente):
    m = simular(REF).massa
    for comp, valor in TABELA_6[corrente].items():
        assert m.correntes[corrente][comp] == pytest.approx(valor)
    assert m.totais[corrente] == pytest.approx(TOTAIS[corrente])


def test_composicoes_tabela_7():
    w = simular(REF).massa.composicoes
    assert w["02"]["MSG"] == pytest.approx(0.08)
    assert w["02"]["Açúcar"] == pytest.approx(0.04)
    assert w["05"]["Água"] == pytest.approx(3200 / 3712)
    assert w["05"]["MSG"] == pytest.approx(32 / 3712)
    for j in w:  # Eq. (10): soma das frações = 1
        assert sum(w[j].values()) == pytest.approx(1.0)


def test_fechamento_massa_tabela_8():
    m = simular(REF).massa
    assert m.m_acucar_cons == pytest.approx(640)
    for eps in list(m.residuos_equip.values()) + list(m.residuos_comp.values()):
        assert eps == pytest.approx(0.0, abs=1e-9)


# ---------- Capítulo 5: Tabela 11 ----------
def test_balanco_energia_tabela_11():
    e = simular(REF).energia
    assert e.delta_T == pytest.approx(50)
    assert e.Q_kJh == pytest.approx(800_000)
    assert e.Q_kW == pytest.approx(222.2222222)
    assert e.m_U01 == pytest.approx(363.6363636)
    assert e.m_U02 == pytest.approx(e.m_U01)
    assert e.residuo == pytest.approx(0.0, abs=1e-6)
    assert e.erro_relativo == pytest.approx(0.0, abs=1e-9)
    assert e.q_MSG == pytest.approx(2777.7777778)


# ---------- Relações generalizadas, Eq. (49)-(53) ----------
@pytest.mark.parametrize("y", RENDIMENTOS_CENARIOS)
def test_relacoes_generalizadas(y):
    p = replace(REF, Y_MSG=y)
    m = simular(p).massa
    base = p.m01 * p.w_acucar_01 * p.X
    assert m.totais["04"] == pytest.approx(base * y * p.eta_MSG)                          # (49)
    assert m.correntes["05"]["MSG"] == pytest.approx(base * y * (1 - p.eta_MSG))          # (50)
    assert m.correntes["02"]["Outros produtos"] == pytest.approx(base * (1 - y))          # (51)
    assert m.totais["05"] == pytest.approx(p.m01 * (1 - p.w_acucar_01 * p.X * y * p.eta_MSG))  # (52)
    assert m.totais["04"] + m.totais["05"] == pytest.approx(p.m01)                        # (53)


def test_carga_termica_independe_do_rendimento():
    """Seção 5.8: os quatro cenários têm a mesma demanda energética."""
    df = simular_cenarios(REF)
    assert df["Carga térmica (kW)"].nunique() == 1
    assert df["MSG recuperado - m04 (kg/h)"].tolist() == pytest.approx([230.4, 259.2, 288.0, 316.8])


# ---------- Domínio do modelo ----------
@pytest.mark.parametrize("campo, valor", [
    ("m01", -1), ("w_acucar_01", 1.2), ("X", -0.1), ("Y_MSG", 1.1),
    ("eta_MSG", 1.5), ("cp", 0), ("lambda_v", -5), ("T03", 20),
])
def test_entradas_invalidas_sao_rejeitadas(campo, valor):
    with pytest.raises(ValueError):
        simular(replace(REF, **{campo: valor}))


def test_produto_nulo_nao_divide_por_zero():
    r = simular(replace(REF, eta_MSG=0.0))
    assert r.energia.q_MSG is None
    assert r.massa.composicoes["04"]["MSG"] == 0.0
