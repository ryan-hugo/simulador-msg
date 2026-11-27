"""ETAPAS 7, 8 e 9 - Interface gráfica do simulador (Streamlit).

Execute:  streamlit run app.py
O navegador abrirá em http://localhost:8501

Como o Streamlit funciona:
    O script inteiro é executado de cima para baixo toda vez que o usuário
    altera um campo. Por isso não há "botão calcular": cada mudança na barra
    lateral gera um novo ParametrosProcesso e uma nova simulação.

Observe que este arquivo NÃO contém nenhuma equação. Toda a matemática está
no pacote `simulador/`; aqui apenas lemos entradas e exibimos resultados.
"""

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from simulador.parametros import ParametrosProcesso
from simulador.simulacao import (
    RENDIMENTOS_CENARIOS,
    simular,
    simular_cenarios,
    tabela_composicoes,
    tabela_energia,
    tabela_fechamento_componentes,
    tabela_vazoes,
)

st.set_page_config(page_title="Simulador MSG", page_icon="🏭", layout="wide")
REF = ParametrosProcesso()


def br(valor, casas=2):
    """Formata número no padrão brasileiro: 3200.5 -> '3.200,50'."""
    if valor is None or valor != valor:  # None ou NaN
        return "—"
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


# ----------------------------------------------------------------------
# Barra lateral: parâmetros de entrada (Etapa 3)
# ----------------------------------------------------------------------
st.sidebar.header("Parâmetros de entrada")
if st.sidebar.button("Restaurar condição de referência"):
    for k in list(st.session_state.keys()):
        del st.session_state[k]

st.sidebar.subheader("Alimentação e fermentação")
m01 = st.sidebar.number_input("Vazão de alimentação, m₀₁ (kg/h)", 0.0, 100000.0, REF.m01, 100.0, key="m01")
w_acucar = st.sidebar.number_input("Fração de açúcar, w_açúcar,01 (kg/kg)", 0.0, 1.0, REF.w_acucar_01, 0.01, key="w")
X = st.sidebar.number_input("Conversão do açúcar, X", 0.0, 1.0, REF.X, 0.01, key="X")
Y_MSG = st.sidebar.select_slider(
    "Rendimento de MSG, Y_MSG (kg/kg)",
    options=[round(0.05 * i, 2) for i in range(21)],
    value=REF.Y_MSG,
    format_func=lambda v: br(v, 2),
    key="Y",
)
st.sidebar.caption(f"Y_OP = 1 − Y_MSG = {br(1 - Y_MSG)} kg/kg (Eq. 18)")

st.sidebar.subheader("Separação")
eta = st.sidebar.number_input("Eficiência de recuperação, η_MSG", 0.0, 1.0, REF.eta_MSG, 0.01, key="eta")

st.sidebar.subheader("Aquecimento (E-101)")
T02 = st.sidebar.number_input("Temperatura de entrada, T₀₂ (°C)", -20.0, 200.0, REF.T02, 1.0, key="T02")
T03 = st.sidebar.number_input("Temperatura de saída, T₀₃ (°C)", -20.0, 200.0, REF.T03, 1.0, key="T03")
cp = st.sidebar.number_input("Calor específico, cp (kJ/kg·K)", 0.0, 10.0, REF.cp, 0.1, key="cp")
lam = st.sidebar.number_input("Calor latente, λv (kJ/kg)", 0.0, 3000.0, REF.lambda_v, 10.0, key="lam")

p = ParametrosProcesso(m01=m01, w_acucar_01=w_acucar, X=X, Y_MSG=Y_MSG, eta_MSG=eta,
                       T02=T02, T03=T03, cp=cp, lambda_v=lam)

# ----------------------------------------------------------------------
# Cabeçalho
# ----------------------------------------------------------------------
st.title("Simulador do processo de produção de glutamato monossódico (MSG)")
st.caption("Fermentador R-101 → Trocador de calor E-101 → Separador S-101 · regime permanente · base: 1 h de operação")

try:
    r = simular(p)
except ValueError as erro:
    st.error("Parâmetros fora do domínio do modelo:\n\n" + str(erro).replace("\n", "\n\n"))
    st.stop()

m, e = r.massa, r.energia

# Indicadores principais
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("MSG recuperado (04)", f"{br(m.totais['04'])} kg/h")
c2.metric("MSG perdido (05)", f"{br(m.correntes['05']['MSG'])} kg/h")
c3.metric("Carga térmica", f"{br(e.Q_kW)} kW")
c4.metric("Vapor (U01)", f"{br(e.m_U01)} kg/h")
c5.metric("Energia específica", f"{br(e.q_MSG, 0)} kJ/kg")

aba_massa, aba_energia, aba_verif, aba_cen = st.tabs(
    ["Balanço de massa", "Balanço de energia", "Verificação", "Cenários de rendimento"]
)

# ----------------------------------------------------------------------
# Aba 1 - Balanço de massa
# ----------------------------------------------------------------------
with aba_massa:
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Vazões mássicas (kg/h)")
        st.dataframe(tabela_vazoes(m).style.format(br), width="stretch")
    with col_b:
        st.subheader("Composições mássicas (%)")
        st.dataframe(tabela_composicoes(m).style.format(lambda v: br(v, 3)), width="stretch")

    st.subheader("Fluxo de massa entre as correntes")
    rot = ["01 Solução açucarada", "R-101 Fermentador", "E-101 Trocador", "S-101 Separador",
           "04 MSG recuperado", "05 Corrente residual"]
    sankey = go.Figure(go.Sankey(
        node=dict(label=rot, pad=20, thickness=18),
        link=dict(
            source=[0, 1, 2, 3, 3],
            target=[1, 2, 3, 4, 5],
            value=[m.totais["01"], m.totais["02"], m.totais["03"], m.totais["04"], m.totais["05"]],
        ),
    ))
    sankey.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(sankey, width="stretch")

# ----------------------------------------------------------------------
# Aba 2 - Balanço de energia
# ----------------------------------------------------------------------
with aba_energia:
    st.subheader("Resultados do trocador de calor E-101")
    st.dataframe(tabela_energia(r).style.format(lambda v: br(v, 4), subset=["Resultado"]), width="stretch")
    st.latex(r"\dot Q_{E-101} = \dot m_{02}\,c_p\,(T_{03}-T_{02}) = \dot m_{U01}\,\lambda_v \qquad (62)")

# ----------------------------------------------------------------------
# Aba 3 - Verificação dos fechamentos
# ----------------------------------------------------------------------
with aba_verif:
    st.subheader("Resíduo do balanço de massa por equipamento (kg/h) – Eq. (44) a (48)")
    st.dataframe({k: [f"{v:.3e}"] for k, v in m.residuos_equip.items()}, width="stretch")
    st.subheader("Fechamento global por componente (kg/h) – Tabela 8")
    st.dataframe(tabela_fechamento_componentes(m).style.format(lambda v: br(v, 3)), width="stretch")
    st.subheader("Balanço de energia – Eq. (69) e (71)")
    st.write(f"Resíduo energético: **{e.residuo:.3e} kJ/h** · erro relativo: **{e.erro_relativo:.3e} %**")
    tol = 1e-6
    ok = all(abs(v) < tol for v in list(m.residuos_equip.values()) + list(m.residuos_comp.values())) \
        and abs(e.residuo) < tol
    (st.success if ok else st.error)(
        "Balanços fechados: todos os resíduos são nulos (tolerância 10⁻⁶)." if ok
        else "Atenção: há resíduo acima da tolerância."
    )

# ----------------------------------------------------------------------
# Aba 4 - Cenários de rendimento (Etapas 8 e 9)
# ----------------------------------------------------------------------
with aba_cen:
    st.write("Os quatro rendimentos do enunciado são simulados mantendo os demais parâmetros da barra lateral.")
    df = simular_cenarios(p, RENDIMENTOS_CENARIOS)
    st.dataframe(df.style.format(lambda v: br(v, 3)), width="stretch", hide_index=True)

    df_plot = df.assign(Rendimento=df["Y_MSG (kg/kg)"].map(lambda v: f"{v:.2f}"))
    g1, g2 = st.columns(2)
    with g1:
        fig = px.bar(
            df_plot, x="Rendimento",
            y=["MSG recuperado - m04 (kg/h)", "MSG perdido (kg/h)"],
            barmode="stack", labels={"value": "Vazão (kg/h)", "variable": ""},
            title="Destino do MSG formado",
        )
        fig.update_layout(legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, width="stretch")
    with g2:
        fig = px.line(
            df_plot, x="Rendimento", y="Energia específica (kJ/kg MSG)", markers=True,
            title="Energia térmica por kg de MSG recuperado",
        )
        st.plotly_chart(fig, width="stretch")

    g3, g4 = st.columns(2)
    with g3:
        fig = px.bar(
            df_plot, x="Rendimento", y=["MSG formado (kg/h)", "Outros produtos (kg/h)"],
            barmode="group", labels={"value": "Vazão (kg/h)", "variable": ""},
            title="Distribuição do açúcar consumido entre os produtos",
        )
        fig.update_layout(legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, width="stretch")
    with g4:
        fig = px.line(
            df_plot, x="Rendimento", y=["MSG no caldo 02 (%)", "MSG no resíduo 05 (%)"], markers=True,
            labels={"value": "Fração mássica (%)", "variable": ""},
            title="Teor de MSG nas correntes",
        )
        fig.update_layout(legend=dict(orientation="h", y=-0.25))
        st.plotly_chart(fig, width="stretch")

    st.download_button(
        "Baixar resultados dos cenários (CSV)",
        df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="cenarios_MSG.csv",
        mime="text/csv",
    )
