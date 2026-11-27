"""ETAPAS 8 e 9 - Integração dos balanços, cenários de rendimento e tabelas.

Este módulo junta os dois balanços em uma única chamada (`simular`) e
organiza os resultados em tabelas do pandas (DataFrame), que depois são
exibidas pela interface e usadas nos gráficos.
"""

from dataclasses import dataclass, replace

import pandas as pd

from .balanco_energia import ResultadoEnergia, calcular_balanco_energia
from .balanco_massa import COMPONENTES, CORRENTES, ResultadoMassa, calcular_balanco_massa
from .parametros import ParametrosProcesso

# Os quatro rendimentos de formação de MSG do enunciado (Seção 4.8.3)
RENDIMENTOS_CENARIOS = (0.40, 0.45, 0.50, 0.55)


@dataclass
class ResultadoSimulacao:
    parametros: ParametrosProcesso
    massa: ResultadoMassa
    energia: ResultadoEnergia


def simular(p: ParametrosProcesso) -> ResultadoSimulacao:
    """Algoritmo principal: valida -> balanço de massa -> balanço de energia."""
    p.validar()
    massa = calcular_balanco_massa(p)
    energia = calcular_balanco_energia(p, m02=massa.totais["02"], m04=massa.totais["04"])
    return ResultadoSimulacao(p, massa, energia)


def simular_cenarios(p_base: ParametrosProcesso, rendimentos=RENDIMENTOS_CENARIOS) -> pd.DataFrame:
    """Executa a simulação para cada rendimento, mantendo os demais parâmetros.

    `replace(p_base, Y_MSG=y)` cria uma cópia dos parâmetros alterando apenas Y_MSG;
    o Y_OP acompanha automaticamente (Eq. 18).
    """
    linhas = []
    for y in rendimentos:
        r = simular(replace(p_base, Y_MSG=y))
        m, e = r.massa, r.energia
        linhas.append({
            "Y_MSG (kg/kg)": y,
            "Y_OP (kg/kg)": r.parametros.Y_OP,
            "MSG formado (kg/h)": m.correntes["02"]["MSG"],
            "MSG recuperado - m04 (kg/h)": m.totais["04"],
            "MSG perdido (kg/h)": m.correntes["05"]["MSG"],
            "Outros produtos (kg/h)": m.correntes["02"]["Outros produtos"],
            "Corrente residual - m05 (kg/h)": m.totais["05"],
            "MSG no caldo 02 (%)": 100 * m.composicoes["02"]["MSG"],
            "MSG no resíduo 05 (%)": 100 * m.composicoes["05"]["MSG"],
            "Carga térmica (kW)": e.Q_kW,
            "Vapor U01 (kg/h)": e.m_U01,
            "Energia específica (kJ/kg MSG)": e.q_MSG,
            "Resíduo de massa global (kg/h)": m.residuos_equip["Global"],
            "Resíduo de energia (kJ/h)": e.residuo,
        })
    return pd.DataFrame(linhas)


def tabela_vazoes(m: ResultadoMassa) -> pd.DataFrame:
    """Reproduz a Tabela 6 (vazões por componente e corrente, kg/h)."""
    df = pd.DataFrame({j: [m.correntes[j][i] for i in COMPONENTES] for j in CORRENTES}, index=COMPONENTES)
    df.loc["Total"] = [m.totais[j] for j in CORRENTES]
    df.index.name = "Componente"
    return df


def tabela_composicoes(m: ResultadoMassa) -> pd.DataFrame:
    """Reproduz a Tabela 7 (composições mássicas, %)."""
    df = pd.DataFrame({j: [100 * m.composicoes[j][i] for i in COMPONENTES] for j in CORRENTES}, index=COMPONENTES)
    df.loc["Total"] = df.sum()
    df.index.name = "Componente"
    return df


def tabela_fechamento_componentes(m: ResultadoMassa) -> pd.DataFrame:
    """Reproduz a Tabela 8 (fechamento global por componente, kg/h)."""
    linhas = []
    for i in COMPONENTES:
        linhas.append({
            "Componente": i,
            "Entrada": m.correntes["01"][i],
            "Geração": m.geracao[i],
            "Consumo": m.consumo[i],
            "Saída": m.correntes["04"][i] + m.correntes["05"][i],
            "Resíduo": m.residuos_comp[i],
        })
    df = pd.DataFrame(linhas).set_index("Componente")
    df.loc["Total"] = df.sum()
    return df


def tabela_energia(r: ResultadoSimulacao) -> pd.DataFrame:
    """Reproduz a Tabela 11 (resultados do balanço de energia)."""
    p, e = r.parametros, r.energia
    dados = [
        ("Vazão do caldo fermentado", r.massa.totais["02"], "kg/h"),
        ("Temperatura inicial", p.T02, "°C"),
        ("Temperatura final", p.T03, "°C"),
        ("Variação de temperatura", e.delta_T, "K"),
        ("Carga térmica de aquecimento", e.Q_kJh, "kJ/h"),
        ("Potência térmica", e.Q_kW, "kW"),
        ("Consumo de vapor (U01)", e.m_U01, "kg/h"),
        ("Vazão de condensado (U02)", e.m_U02, "kg/h"),
        ("Resíduo energético", e.residuo, "kJ/h"),
        ("Erro relativo do balanço", e.erro_relativo, "%"),
        ("Energia específica por kg de MSG", e.q_MSG, "kJ/kg"),
    ]
    return pd.DataFrame(dados, columns=["Parâmetro", "Resultado", "Unidade"]).set_index("Parâmetro")
