"""ETAPA 6 - Tabela comparativa: resultado computacional x cálculo analítico.

Execute:  python validar.py
A saída é usada na Seção 6.6 do relatório (validação do modelo computacional).
"""

from simulador.parametros import ParametrosProcesso
from simulador.simulacao import simular

r = simular(ParametrosProcesso())
m, e = r.massa, r.energia

# (descrição, valor analítico do relatório, valor calculado pelo programa, unidade)
comparacoes = [
    ("Açúcar consumido", 640, m.m_acucar_cons, "kg/h"),
    ("MSG formado (02)", 320, m.correntes["02"]["MSG"], "kg/h"),
    ("Outros produtos (02)", 320, m.correntes["02"]["Outros produtos"], "kg/h"),
    ("Açúcar residual (02)", 160, m.correntes["02"]["Açúcar"], "kg/h"),
    ("MSG recuperado (04)", 288, m.totais["04"], "kg/h"),
    ("MSG não recuperado (05)", 32, m.correntes["05"]["MSG"], "kg/h"),
    ("Corrente residual (05)", 3712, m.totais["05"], "kg/h"),
    ("Fração de MSG em 05", 32 / 3712 * 100, m.composicoes["05"]["MSG"] * 100, "%"),
    ("Carga térmica", 800000, e.Q_kJh, "kJ/h"),
    ("Potência térmica", 800000 / 3600, e.Q_kW, "kW"),
    ("Vazão de vapor (U01)", 800000 / 2200, e.m_U01, "kg/h"),
    ("Energia específica", 800000 / 288, e.q_MSG, "kJ/kg"),
]

print(f"{'Grandeza':<26}{'Analítico':>14}{'Computacional':>16}{'Desvio (%)':>12}  Unidade")
for nome, analitico, calculado, un in comparacoes:
    desvio = abs(calculado - analitico) / abs(analitico) * 100
    print(f"{nome:<26}{analitico:>14.4f}{calculado:>16.4f}{desvio:>12.2e}  {un}")

print("\nResíduos de massa por equipamento (kg/h):", m.residuos_equip)
print("Resíduos de massa por componente (kg/h):", m.residuos_comp)
print(f"Resíduo de energia: {e.residuo:.3e} kJ/h | erro relativo: {e.erro_relativo:.3e} %")
