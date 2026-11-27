"""ETAPA 4 - Implementação dos balanços de massa (Capítulo 4).

Cada linha de cálculo traz o número da equação correspondente no relatório,
para que o código possa ser conferido diretamente com o texto.

Representação das correntes:
    Cada corrente é um dicionário {componente: vazão em kg/h}, por exemplo
        corrente_02 = {"Água": 3200, "Açúcar": 160, "MSG": 320, "Outros produtos": 320}
    Esse formato reproduz a notação m_{i,j} (componente i, corrente j).
"""

from dataclasses import dataclass

from .parametros import ParametrosProcesso

COMPONENTES = ("Água", "Açúcar", "MSG", "Outros produtos")
CORRENTES = ("01", "02", "03", "04", "05")


@dataclass
class ResultadoMassa:
    correntes: dict      # {"01": {"Água": ..., ...}, ...}           m_{i,j}  [kg/h]
    totais: dict         # {"01": 4000.0, ...}                        m_j      [kg/h]
    composicoes: dict    # {"01": {"Água": 0.8, ...}, ...}            w_{i,j}  [kg/kg]
    m_acucar_cons: float # açúcar consumido no fermentador            [kg/h]
    geracao: dict        # termos G_i do fermentador                  [kg/h]
    consumo: dict        # termos C_i do fermentador                  [kg/h]
    residuos_equip: dict # ε_m por equipamento e global, Eq. (44)-(48) [kg/h]
    residuos_comp: dict  # ε por componente, Eq. (6) / Tabela 8       [kg/h]


def total(corrente: dict) -> float:
    """Vazão total da corrente: soma das vazões dos componentes. Eq. (8)"""
    return sum(corrente.values())


def fracoes(corrente: dict) -> dict:
    """Frações mássicas w_{i,j} = m_{i,j} / m_j. Eq. (9)

    Se a corrente tiver vazão nula, devolve frações nulas (evita divisão por zero).
    """
    m = total(corrente)
    return {i: (corrente[i] / m if m > 0 else 0.0) for i in COMPONENTES}


def calcular_balanco_massa(p: ParametrosProcesso) -> ResultadoMassa:
    p.validar()

    # ------------------------------------------------------------------
    # Corrente 01 - Solução açucarada (Seção 4.4.1)
    # ------------------------------------------------------------------
    m_acucar_01 = p.m01 * p.w_acucar_01                  # Eq. (12)
    m_agua_01 = p.m01 * p.w_agua_01                      # Eq. (13)
    c01 = {"Água": m_agua_01, "Açúcar": m_acucar_01, "MSG": 0.0, "Outros produtos": 0.0}

    # ------------------------------------------------------------------
    # Fermentador R-101 (Seções 4.4.2 a 4.4.4)
    # ------------------------------------------------------------------
    m_acucar_cons = p.X * m_acucar_01                    # Eq. (15)
    m_acucar_02 = (1.0 - p.X) * m_acucar_01              # Eq. (16)
    m_MSG_02 = p.Y_MSG * m_acucar_cons                   # Eq. (19)
    m_OP_02 = p.Y_OP * m_acucar_cons                     # Eq. (20)
    m_agua_02 = m_agua_01                                # Eq. (21)
    c02 = {"Água": m_agua_02, "Açúcar": m_acucar_02, "MSG": m_MSG_02, "Outros produtos": m_OP_02}

    # ------------------------------------------------------------------
    # Trocador de calor E-101 (Seção 4.5): nada muda na composição
    # dict(c02) cria uma CÓPIA; assim alterar c03 não alteraria c02.
    # ------------------------------------------------------------------
    c03 = dict(c02)                                      # Eq. (27)-(29)

    # ------------------------------------------------------------------
    # Separador S-101 (Seção 4.6)
    # ------------------------------------------------------------------
    m_MSG_04 = p.eta_MSG * c03["MSG"]                    # Eq. (33)
    m_MSG_05 = (1.0 - p.eta_MSG) * c03["MSG"]            # Eq. (34)
    c04 = {"Água": 0.0, "Açúcar": 0.0, "MSG": m_MSG_04, "Outros produtos": 0.0}
    c05 = {
        "Água": c03["Água"],                             # Eq. (35)
        "Açúcar": c03["Açúcar"],                         # Eq. (36)
        "MSG": m_MSG_05,
        "Outros produtos": c03["Outros produtos"],       # Eq. (37)
    }

    correntes = {"01": c01, "02": c02, "03": c03, "04": c04, "05": c05}
    totais = {j: total(c) for j, c in correntes.items()}        # Eq. (8)
    composicoes = {j: fracoes(c) for j, c in correntes.items()} # Eq. (9)

    # ------------------------------------------------------------------
    # Verificação do fechamento (Seção 4.8)  ε = entradas - saídas
    # ------------------------------------------------------------------
    residuos_equip = {
        "R-101": totais["01"] - totais["02"],                    # Eq. (45)
        "E-101": totais["02"] - totais["03"],                    # Eq. (46)
        "S-101": totais["03"] - (totais["04"] + totais["05"]),   # Eq. (47)
        "Global": totais["01"] - (totais["04"] + totais["05"]),  # Eq. (48)
    }

    geracao = {"Água": 0.0, "Açúcar": 0.0, "MSG": m_MSG_02, "Outros produtos": m_OP_02}
    consumo = {"Água": 0.0, "Açúcar": m_acucar_cons, "MSG": 0.0, "Outros produtos": 0.0}
    residuos_comp = {
        # Eq. (6): entrada + geração = saída + consumo  ->  ε = E + G - S - C
        i: c01[i] + geracao[i] - (c04[i] + c05[i]) - consumo[i]
        for i in COMPONENTES
    }

    return ResultadoMassa(
        correntes=correntes,
        totais=totais,
        composicoes=composicoes,
        m_acucar_cons=m_acucar_cons,
        geracao=geracao,
        consumo=consumo,
        residuos_equip=residuos_equip,
        residuos_comp=residuos_comp,
    )
