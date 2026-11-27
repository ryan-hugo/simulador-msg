"""ETAPA 5 - Implementação dos balanços de energia (Capítulo 5).

O balanço é aplicado somente ao trocador de calor E-101 (Seção 5.1).
A relação fundamental é a Eq. (62):

    Q_E-101 = m02 · cp · (T03 - T02) = mU01 · λv

Recomendação da Seção 5.7: manter a precisão total nos cálculos internos
e arredondar apenas na apresentação. Por isso NENHUMA função aqui usa round().
"""

from dataclasses import dataclass

from .parametros import ParametrosProcesso

SEGUNDOS_POR_HORA = 3600.0


@dataclass
class ResultadoEnergia:
    delta_T: float          # Variação de temperatura do caldo      [K]
    Q_kJh: float            # Carga térmica de aquecimento          [kJ/h]
    Q_kW: float             # Potência térmica                      [kW]
    m_U01: float            # Vazão de vapor                        [kg/h]
    m_U02: float            # Vazão de condensado                   [kg/h]
    Q_vapor: float          # Energia cedida pelo vapor             [kJ/h]
    residuo: float          # ε_E                                   [kJ/h]
    erro_relativo: float    # e_E                                   [%]
    q_MSG: float | None     # Energia específica por kg de MSG      [kJ/kg] (None se m04 = 0)


def calcular_balanco_energia(p: ParametrosProcesso, m02: float, m04: float) -> ResultadoEnergia:
    """Recebe a vazão do caldo (m02) e a de MSG recuperado (m04), vindas do balanço de massa."""
    p.validar()

    delta_T = p.T03 - p.T02                              # Eq. (63)
    Q_kJh = m02 * p.cp * delta_T                         # Eq. (62) e (64)
    Q_kW = Q_kJh / SEGUNDOS_POR_HORA                     # Eq. (65)
    m_U01 = Q_kJh / p.lambda_v                           # Eq. (66)
    m_U02 = m_U01                                        # Eq. (60) e (68)

    # Verificação do fechamento (Seção 5.7)
    Q_vapor = m_U01 * p.lambda_v                         # Eq. (70)
    residuo = Q_vapor - Q_kJh                            # Eq. (69)
    erro_relativo = residuo / Q_vapor * 100.0 if Q_vapor > 0 else 0.0   # Eq. (71)

    # Indicador de desempenho (Seção 5.8)
    q_MSG = Q_kJh / m04 if m04 > 0 else None             # Eq. (72)

    return ResultadoEnergia(delta_T, Q_kJh, Q_kW, m_U01, m_U02, Q_vapor, residuo, erro_relativo, q_MSG)
