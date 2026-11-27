"""Gera o Capítulo 6 (Desenvolvimento do modelo computacional) em .docx padronizado (ABNT).

Usa o documento do Capítulo 5 como modelo de estilos (fonte, margens, títulos),
e calcula as tabelas de validação executando o próprio simulador.

Execute na raiz do projeto:  python docs/gerar_capitulo6.py
"""

import re
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from simulador.parametros import ParametrosProcesso  # noqa: E402
from simulador.simulacao import RENDIMENTOS_CENARIOS, simular  # noqa: E402

MODELO = Path.home() / "Downloads" / "Balancos_de_energia_MSG_Capitulo_5.docx"
SAIDA = Path.home() / "Downloads" / "Desenvolvimento_modelo_computacional_MSG_Capitulo_6.docx"
FIG_DIR = RAIZ / "docs" / "figuras"
LARGURA_UTIL = 9071  # twips (16 cm)


def br(v, casas=2):
    t = f"{v:,.{casas}f}"
    return t.replace(",", "X").replace(".", ",").replace("X", ".")


# ======================================================================
# Utilitários de formatação (reproduzem o padrão do Capítulo 5)
# ======================================================================
doc = Document(str(MODELO))
corpo = doc.element.body
for el in list(corpo):
    if el.tag != qn("w:sectPr"):
        corpo.remove(el)

contadores = {"tabela": 11, "quadro": 0, "figura": 1, "eq": 72}


def h1(t):
    doc.add_paragraph(t, style="Heading 1")


def h2(t):
    doc.add_paragraph(t, style="Heading 2")


def h3(t):
    doc.add_paragraph(t, style="Heading 3")


def par(t):
    """Parágrafo de texto. Trechos entre **dois asteriscos** ficam em negrito, entre *um asterisco* em itálico."""
    p = doc.add_paragraph(style="Normal")
    for pedaco in re.split(r"(\*\*[^*]+\*\*|\*[^*]+\*|~[^~]+~)", t):
        if not pedaco:
            continue
        if pedaco.startswith("~") and pedaco.endswith("~") and len(pedaco) > 2:
            p.add_run(pedaco[1:-1]).font.subscript = True
            continue
        if pedaco.startswith("**"):
            p.add_run(pedaco[2:-2]).bold = True
        elif pedaco.startswith("*") and pedaco.endswith("*") and len(pedaco) > 2:
            p.add_run(pedaco[1:-1]).italic = True
        else:
            p.add_run(pedaco)
    return p


def item(t):
    p = par(t)
    p.paragraph_format.left_indent = Cm(1.25)
    p.paragraph_format.first_line_indent = Cm(-0.5)
    return p


def _p_xml(texto, spacing, extra_ppr="", sz=None, keep_next=False):
    rpr = f"<w:rPr><w:sz w:val=\"{sz}\"/></w:rPr>" if sz else ""
    kn = "<w:keepNext/>" if keep_next else ""
    return parse_xml(
        f'<w:p {nsdecls("w")}><w:pPr>{kn}{spacing}<w:ind w:firstLine="0"/>{extra_ppr}</w:pPr>'
        f'<w:r>{rpr}<w:t xml:space="preserve">{escape(texto)}</w:t></w:r></w:p>'
    )


def legenda(tipo, titulo):
    contadores[tipo] += 1
    n = contadores[tipo]
    rotulo = {"tabela": "Tabela", "quadro": "Quadro", "figura": "Figura"}[tipo]
    corpo.insert(len(corpo) - 1, _p_xml(
        f"{rotulo} {n} – {titulo}",
        '<w:spacing w:line="240" w:lineRule="auto" w:before="160" w:after="80"/>',
        keep_next=True,
    ))
    return n


def fonte(t="Fonte: Elaborado pelos autores (2026)."):
    corpo.insert(len(corpo) - 1, _p_xml(
        t, '<w:spacing w:line="240" w:lineRule="auto" w:before="60" w:after="160"/>', sz=20,
    ))


def _cel(texto, largura, alin, negrito=False, borda_inf=False, ultima=False):
    b = "<w:b/>" if negrito else ""
    bordas = '<w:tcBorders><w:bottom w:val="single" w:sz="4" w:color="000000"/></w:tcBorders>' if borda_inf else ""
    kn = "" if ultima else "<w:keepNext/>"
    return (
        f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{largura}"/><w:vAlign w:val="center"/>{bordas}</w:tcPr>'
        f'<w:p><w:pPr>{kn}<w:spacing w:line="240" w:lineRule="auto" w:before="60" w:after="60"/>'
        f'<w:ind w:firstLine="0"/><w:jc w:val="{alin}"/></w:pPr>'
        f'<w:r><w:rPr>{b}<w:sz w:val="22"/></w:rPr><w:t xml:space="preserve">{escape(str(texto))}</w:t></w:r></w:p></w:tc>'
    )


def tabela(titulo, cabecalho, linhas, larguras, alinhamentos=None, negrito_ultima=False):
    legenda("tabela", titulo)
    total = sum(larguras)
    larguras = [round(w * LARGURA_UTIL / total) for w in larguras] if total > LARGURA_UTIL else larguras
    alinhamentos = alinhamentos or (["left"] + ["center"] * (len(cabecalho) - 1))
    grid = "".join(f'<w:gridCol w:w="{w}"/>' for w in larguras)
    xml = (
        f'<w:tbl {nsdecls("w")}><w:tblPr><w:tblW w:type="auto" w:w="0"/><w:jc w:val="center"/>'
        '<w:tblLayout w:type="fixed"/><w:tblBorders><w:top w:val="single" w:sz="4" w:color="000000"/>'
        '<w:bottom w:val="single" w:sz="4" w:color="000000"/></w:tblBorders></w:tblPr>'
        f"<w:tblGrid>{grid}</w:tblGrid>"
        '<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>'
        + "".join(_cel(c, w, a, True, True) for c, w, a in zip(cabecalho, larguras, alinhamentos))
        + "</w:tr>"
    )
    for k, linha in enumerate(linhas):
        ultima = k == len(linhas) - 1
        neg = negrito_ultima and ultima
        borda = negrito_ultima and k == len(linhas) - 2
        xml += '<w:tr><w:trPr><w:cantSplit/></w:trPr>' + "".join(
            _cel(c, w, a, neg, borda, ultima) for c, w, a in zip(linha, larguras, alinhamentos)
        ) + "</w:tr>"
    xml += "</w:tbl>"
    corpo.insert(len(corpo) - 1, parse_xml(xml))
    fonte()


def quadro_codigo(titulo, codigo, fonte_txt="Fonte: Elaborado pelos autores (2026)."):
    legenda("quadro", titulo)
    linhas = codigo.strip("\n").split("\n")
    paras = ""
    for k, ln in enumerate(linhas):
        kn = "" if k == len(linhas) - 1 else "<w:keepNext/>"
        paras += (
            f'<w:p><w:pPr>{kn}<w:spacing w:line="240" w:lineRule="auto" w:before="0" w:after="0"/>'
            '<w:ind w:firstLine="0"/><w:jc w:val="left"/></w:pPr>'
            '<w:r><w:rPr><w:rFonts w:ascii="Courier New" w:hAnsi="Courier New" w:cs="Courier New"/>'
            f'<w:sz w:val="17"/></w:rPr><w:t xml:space="preserve">{escape(ln) or " "}</w:t></w:r></w:p>'
        )
    borda = '<w:{0} w:val="single" w:sz="4" w:color="000000"/>'
    xml = (
        f'<w:tbl {nsdecls("w")}><w:tblPr><w:tblW w:type="dxa" w:w="{LARGURA_UTIL}"/><w:jc w:val="center"/>'
        "<w:tblBorders>" + "".join(borda.format(s) for s in ("top", "left", "bottom", "right")) + "</w:tblBorders>"
        '<w:tblCellMar><w:top w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/>'
        '<w:bottom w:w="80" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tblCellMar></w:tblPr>'
        f'<w:tblGrid><w:gridCol w:w="{LARGURA_UTIL}"/></w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr>'
        f'<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="{LARGURA_UTIL}"/><w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/></w:tcPr>'
        f"{paras}</w:tc></w:tr></w:tbl>"
    )
    corpo.insert(len(corpo) - 1, parse_xml(xml))
    fonte(fonte_txt)


def figura(titulo, caminho, largura_cm=15.0):
    legenda("figura", titulo)
    p = doc.add_paragraph(style="Normal")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.first_line_indent = Cm(0)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.line_spacing = 1.0
    p.add_run().add_picture(str(caminho), width=Cm(largura_cm))
    fonte()


# ---------------- Equações (OMML editável) ----------------
def mr(t, normal=False):
    sty = '<m:rPr><m:sty m:val="p"/></m:rPr>' if normal else ""
    return f'<m:r>{sty}<m:t xml:space="preserve">{escape(t)}</m:t></m:r>'


def msub(base, s):
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>"


def msup(base, s):
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{s}</m:sup></m:sSup>"


def mfrac(n, d):
    return f"<m:f><m:num>{n}</m:num><m:den>{d}</m:den></m:f>"


def mdelim(conteudo, ini="(", fim=")"):
    return (f'<m:d><m:dPr><m:begChr m:val="{ini}"/><m:endChr m:val="{fim}"/></m:dPr>'
            f"<m:e>{conteudo}</m:e></m:d>")


def mdot(base):
    return f'<m:acc><m:accPr><m:chr m:val="&#775;"/></m:accPr><m:e>{base}</m:e></m:acc>'


def equacao(omml):
    contadores["eq"] += 1
    n = contadores["eq"]
    xml = (
        f'<w:p {nsdecls("w", "m")}><w:pPr><w:tabs><w:tab w:val="center" w:pos="4535"/>'
        '<w:tab w:val="right" w:pos="9071"/></w:tabs>'
        '<w:spacing w:line="276" w:lineRule="auto" w:before="60" w:after="60"/>'
        '<w:ind w:firstLine="0"/><w:jc w:val="left"/></w:pPr>'
        f"<w:r><w:tab/></w:r><m:oMath>{omml}</m:oMath><w:r><w:tab/><w:t>({n})</w:t></w:r></w:p>"
    )
    corpo.insert(len(corpo) - 1, parse_xml(xml))
    return n


def m_ij(i, j):
    return msub(mdot(mr("m")), mr(f"{i},{j}") if i else mr(j))


# ======================================================================
# Figura do algoritmo
# ======================================================================
def gerar_fluxograma(caminho):
    plt.rcParams["font.family"] = "Times New Roman"
    fig, ax = plt.subplots(figsize=(7.2, 9.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 13.2)
    ax.axis("off")

    def caixa(y, texto, sub=None, cor="#FFFFFF", borda="#000000", x=5, w=6.2, h=0.82, arred=0.12):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h, boxstyle=f"round,pad=0,rounding_size={arred}",
                                    fc=cor, ec=borda, lw=1.1))
        if sub:
            ax.text(x, y + 0.13, texto, ha="center", va="center", fontsize=10.5, fontweight="bold")
            ax.text(x, y - 0.19, sub, ha="center", va="center", fontsize=8.8)
        else:
            ax.text(x, y, texto, ha="center", va="center", fontsize=10.5, fontweight="bold")

    def seta(y1, y2, x=5):
        ax.annotate("", xy=(x, y2), xytext=(x, y1), arrowprops=dict(arrowstyle="-|>", lw=1.0, color="black"))

    ys = [12.6, 11.45, 10.05, 8.75, 7.65, 6.55, 5.45, 4.35, 3.25, 2.15, 1.0]
    caixa(ys[0], "Início", w=2.4, h=0.6, arred=0.3)
    seta(ys[0] - 0.3, ys[1] + 0.41)
    caixa(ys[1], "Leitura dos parâmetros de entrada",
          "m₀₁, w_açúcar,01, X, Y_MSG, η_MSG, T₀₂, T₀₃, cp, λv  —  Eq. (73)")
    seta(ys[1] - 0.41, ys[2] + 0.62)
    # losango de validação
    ax.add_patch(Polygon([(5, ys[2] + 0.62), (7.4, ys[2]), (5, ys[2] - 0.62), (2.6, ys[2])], closed=True,
                         fc="#FFFFFF", ec="black", lw=1.1))
    ax.text(5, ys[2] + 0.08, "Parâmetros dentro", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.text(5, ys[2] - 0.22, "do domínio?", ha="center", va="center", fontsize=10, fontweight="bold")
    ax.annotate("", xy=(8.3, ys[2]), xytext=(7.4, ys[2]), arrowprops=dict(arrowstyle="-|>", lw=1.0))
    ax.text(7.85, ys[2] + 0.17, "Não", ha="center", fontsize=9)
    caixa(ys[2], "Mensagem", "de erro", x=9.1, w=1.65, h=0.82)
    ax.text(5.25, ys[2] - 0.86, "Sim", fontsize=9)
    seta(ys[2] - 0.62, ys[3] + 0.41)
    caixa(ys[3], "Balanço de massa no fermentador R-101", "Eq. (12) a (26)")
    seta(ys[3] - 0.41, ys[4] + 0.41)
    caixa(ys[4], "Balanço de massa no trocador E-101", "Eq. (27) a (30)")
    seta(ys[4] - 0.41, ys[5] + 0.41)
    caixa(ys[5], "Balanço de massa no separador S-101", "Eq. (31) a (43)")
    seta(ys[5] - 0.41, ys[6] + 0.41)
    caixa(ys[6], "Balanço de energia no trocador E-101", "Eq. (62) a (68) e (72)")
    seta(ys[6] - 0.41, ys[7] + 0.41)
    caixa(ys[7], "Verificação dos fechamentos", "Eq. (44) a (48), (69) e (71)")
    seta(ys[7] - 0.41, ys[8] + 0.41)
    caixa(ys[8], "Simulação dos cenários de rendimento", "Y_MSG = 0,40; 0,45; 0,50; 0,55")
    seta(ys[8] - 0.41, ys[9] + 0.41)
    caixa(ys[9], "Apresentação dos resultados", "tabelas, indicadores e gráficos")
    seta(ys[9] - 0.41, ys[10] + 0.3)
    caixa(ys[10], "Fim", w=2.4, h=0.6, arred=0.3)
    fig.savefig(caminho, dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ======================================================================
# Dados calculados pelo próprio simulador
# ======================================================================
REF = ParametrosProcesso()
res = simular(REF)
mm, ee = res.massa, res.energia

comparacoes = [
    ("Açúcar consumido", "(15)", 640, mm.m_acucar_cons, "kg/h"),
    ("MSG formado (02)", "(19)", 320, mm.correntes["02"]["MSG"], "kg/h"),
    ("Outros produtos (02)", "(20)", 320, mm.correntes["02"]["Outros produtos"], "kg/h"),
    ("Açúcar residual (02)", "(16)", 160, mm.correntes["02"]["Açúcar"], "kg/h"),
    ("MSG recuperado (04)", "(33)", 288, mm.totais["04"], "kg/h"),
    ("MSG não recuperado (05)", "(34)", 32, mm.correntes["05"]["MSG"], "kg/h"),
    ("Vazão da corrente residual (05)", "(38)", 3712, mm.totais["05"], "kg/h"),
    ("Fração mássica de MSG em 05", "(42)", 32 / 3712 * 100, 100 * mm.composicoes["05"]["MSG"], "%"),
    ("Carga térmica", "(64)", 800000, ee.Q_kJh, "kJ/h"),
    ("Potência térmica", "(65)", 800000 / 3600, ee.Q_kW, "kW"),
    ("Vazão de vapor (U01)", "(67)", 800000 / 2200, ee.m_U01, "kg/h"),
    ("Energia específica", "(72)", 800000 / 288, ee.q_MSG, "kJ/kg"),
]


SOBRESCRITO = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def potencia10(exp):
    return "10" + str(exp).translate(SOBRESCRITO)


def desvio_txt(calc, anal):
    d = abs(calc - anal) / abs(anal) * 100
    if d == 0:
        return "0"
    exp = int(f"{d:e}".split("e")[1])
    return f"{br(d / 10 ** exp, 1)} × {potencia10(exp)}"


desvio_max = max(abs(c - a) / abs(a) * 100 for _, _, a, c, _ in comparacoes)

cenarios = []
for y in RENDIMENTOS_CENARIOS:
    from dataclasses import replace
    p = replace(REF, Y_MSG=y)
    r = simular(p)
    base = p.m01 * p.w_acucar_01 * p.X
    m04_a = base * y * p.eta_MSG                                   # Eq. (49)
    m05_a = p.m01 * (1 - p.w_acucar_01 * p.X * y * p.eta_MSG)        # Eq. (52)
    cenarios.append((y, m04_a, r.massa.totais["04"], m05_a, r.massa.totais["05"],
                     r.massa.totais["04"] + r.massa.totais["05"], r.energia.Q_kW))

saida_pytest = subprocess.run(
    [sys.executable, "-m", "pytest", "-q"], cwd=RAIZ, capture_output=True, text=True, encoding="utf-8"
).stdout
n_ok = int(re.search(r"(\d+) passed", saida_pytest).group(1))
n_falha = int(m.group(1)) if (m := re.search(r"(\d+) failed", saida_pytest)) else 0

FIG_DIR.mkdir(parents=True, exist_ok=True)
fluxo = FIG_DIR / "fluxograma_algoritmo.png"
gerar_fluxograma(fluxo)
interface = FIG_DIR / "interface_simulador.png"

# ======================================================================
# TEXTO DO CAPÍTULO
# ======================================================================
h1("6 DESENVOLVIMENTO DO MODELO COMPUTACIONAL")
par("O desenvolvimento do modelo computacional tem por finalidade transformar as formulações matemáticas "
    "estabelecidas nos Capítulos 4 e 5 em um software capaz de calcular, de maneira automática e reprodutível, "
    "as vazões, as composições das correntes e a demanda térmica do processo simplificado de produção de "
    "glutamato monossódico (MSG). A ferramenta resultante permite alterar os parâmetros operacionais e avaliar "
    "rapidamente as consequências dessas alterações, o que seria trabalhoso e suscetível a erros caso os "
    "cálculos fossem refeitos manualmente para cada condição analisada.")
par("O simulador foi concebido segundo uma abordagem determinística e em regime permanente, coerente com as "
    "hipóteses adotadas nos balanços de massa e de energia. Sua construção foi organizada em etapas sucessivas: "
    "configuração do ambiente de desenvolvimento, estruturação do projeto, declaração dos parâmetros de entrada, "
    "implementação dos balanços de massa e de energia, validação matemática, desenvolvimento da interface "
    "gráfica, implementação das simulações e construção de tabelas e gráficos. Este capítulo descreve a "
    "metodologia efetivamente empregada em cada uma dessas etapas, bem como os procedimentos utilizados para "
    "verificar a correspondência entre os resultados computacionais e os cálculos analíticos.")

# ---------------------------------------------------------------- 6.1
h2("6.1 SELEÇÃO E JUSTIFICATIVA DAS FERRAMENTAS COMPUTACIONAIS")
par("A seleção das ferramentas computacionais considerou quatro critérios principais: adequação ao tipo de "
    "problema, disponibilidade gratuita, facilidade de aprendizado e capacidade de produzir uma interface "
    "interativa sem a necessidade de conhecimentos avançados de desenvolvimento web. Como o modelo é composto "
    "por equações algébricas explícitas, não se fez necessário o emprego de simuladores comerciais de processos, "
    "cujos pacotes termodinâmicos e algoritmos de convergência excederiam a complexidade do problema proposto.")
par("A linguagem Python foi adotada como base do software por apresentar sintaxe legível, ampla utilização em "
    "Engenharia Química e em ciência de dados e um extenso ecossistema de bibliotecas científicas. Empregou-se a "
    "versão 3.13, compatível com todas as bibliotecas utilizadas. O código foi escrito no editor Visual Studio "
    "Code, com as extensões Python e Pylance, que oferecem realce de sintaxe, verificação de tipos e execução "
    "integrada ao terminal. As dependências do projeto foram instaladas em um ambiente virtual (*venv*), "
    "recurso que isola as bibliotecas do simulador das demais instalações do computador e garante a "
    "reprodutibilidade da execução em outras máquinas, mediante o arquivo de requisitos do projeto.")
par("A interface gráfica foi construída com a biblioteca Streamlit, que converte scripts Python em aplicações "
    "web interativas executadas no navegador. A organização tabular dos resultados utilizou a biblioteca pandas, "
    "enquanto os gráficos interativos foram elaborados com a biblioteca Plotly. Para a validação automatizada "
    "do modelo, empregou-se o *framework* de testes pytest. A Tabela 12 apresenta as ferramentas utilizadas, "
    "suas versões e respectivas funções no desenvolvimento.")
tabela("Ferramentas computacionais utilizadas no desenvolvimento do simulador.",
       ["Ferramenta", "Versão", "Função no projeto"],
       [["Python", "3.13.2", "Linguagem de programação e execução dos cálculos"],
        ["Visual Studio Code", "—", "Ambiente de edição, organização e execução do código"],
        ["venv", "3.13.2", "Isolamento das dependências do projeto"],
        ["Streamlit", "1.67.0", "Construção da interface gráfica interativa"],
        ["pandas", "3.1.1", "Organização dos resultados em tabelas"],
        ["Plotly", "7.2.0", "Elaboração dos gráficos interativos"],
        ["pytest", "9.2.0", "Execução dos testes automatizados de validação"]],
       [2300, 1100, 5671], ["left", "center", "left"])
par("A combinação dessas ferramentas permitiu separar com clareza a lógica matemática da camada de "
    "apresentação, aspecto considerado essencial para a confiabilidade do software. Dessa forma, as equações "
    "podem ser verificadas de maneira independente da interface, e eventuais modificações na apresentação dos "
    "resultados não interferem nos cálculos.")

# ---------------------------------------------------------------- 6.2
h2("6.2 ESTRUTURA MATEMÁTICA DO MODELO COMPUTACIONAL")
par("O modelo computacional é constituído pelo conjunto de equações algébricas desenvolvidas nos capítulos "
    "anteriores, organizadas de modo que cada variável desconhecida seja calculada a partir de grandezas já "
    "conhecidas. Como o fluxograma não apresenta correntes de reciclo e todas as relações são explícitas, o "
    "sistema pode ser resolvido de forma sequencial, equipamento a equipamento, no mesmo sentido do escoamento "
    "do processo, sem a necessidade de métodos iterativos de convergência. Essa estratégia corresponde à "
    "abordagem sequencial modular, amplamente utilizada em simuladores de processos.")
par("As grandezas especificadas pelo usuário foram reunidas no vetor de parâmetros de entrada, definido pela "
    "Equação (73). Os valores da condição de referência correspondem aos dados das Tabelas 4 e 9.")
equacao(
    mr("p") + mr("=", True) + mdelim(
        msub(mdot(mr("m")), mr("01", True)) + mr(",", True) + msub(mr("w"), mr("açúcar,01", True)) + mr(",", True)
        + mr("X") + mr(",", True) + msub(mr("Y"), mr("MSG", True)) + mr(",", True) + msub(mr("η"), mr("MSG", True))
        + mr(",", True) + msub(mr("T"), mr("02", True)) + mr(",", True) + msub(mr("T"), mr("03", True))
        + mr(",", True) + msub(mr("c"), mr("p")) + mr(",", True) + msub(mr("λ"), mr("v"))
    )
)
par("A partir desse vetor, o simulador determina o conjunto de resultados *R*, composto pelas vazões e frações "
    "mássicas das correntes 01 a 05, pelas vazões das utilidades U01 e U02, pela carga térmica e pelos resíduos "
    "dos balanços. Em termos formais, o modelo pode ser representado como uma função que associa cada conjunto "
    "de parâmetros a um único conjunto de resultados:")
equacao(mr("R") + mr("=", True) + mr("f") + mdelim(mr("p")))
par("A unicidade da solução decorre do fato de que o número de equações independentes é igual ao número de "
    "variáveis desconhecidas, de modo que o sistema não apresenta graus de liberdade remanescentes após a "
    "especificação de *p*. As grandezas derivadas, como a fração mássica de água na alimentação e o rendimento "
    "de formação de outros produtos, não são fornecidas pelo usuário, sendo calculadas internamente pelas "
    "Equações (4) e (18), o que impede a introdução de dados inconsistentes.")
par("Para assegurar que as equações sejam aplicadas apenas dentro de seu domínio de validade, foram "
    "implementadas as restrições indicadas nas Seções 4.8.3 e 5.8. A Tabela 13 relaciona os símbolos "
    "matemáticos às variáveis empregadas no código-fonte e às restrições verificadas antes de qualquer cálculo.")
tabela("Correspondência entre os símbolos matemáticos, as variáveis do código e as restrições de domínio.",
       ["Símbolo", "Variável no código", "Valor de referência", "Restrição"],
       [["ṁ01", "m01", "4.000 kg/h", "ṁ01 ≥ 0"],
        ["w_açúcar,01", "w_acucar_01", "0,20", "0 ≤ w ≤ 1"],
        ["X", "X", "0,80", "0 ≤ X ≤ 1"],
        ["Y_MSG", "Y_MSG", "0,50", "0 ≤ Y_MSG ≤ 1"],
        ["Y_OP", "Y_OP (calculada)", "0,50", "Y_OP = 1 − Y_MSG"],
        ["η_MSG", "eta_MSG", "0,90", "0 ≤ η ≤ 1"],
        ["T02", "T02", "30 °C", "T03 ≥ T02"],
        ["T03", "T03", "80 °C", "T03 ≥ T02"],
        ["cp", "cp", "4,0 kJ/(kg·K)", "cp > 0"],
        ["λv", "lambda_v", "2.200 kJ/kg", "λv > 0"]],
       [1700, 2400, 2000, 2971], ["left", "left", "center", "center"])
par("Adicionalmente, as operações de divisão foram protegidas contra denominadores nulos. As frações mássicas "
    "de uma corrente com vazão total igual a zero são definidas como nulas, e a energia térmica específica, "
    "calculada pela Equação (72), somente é avaliada quando a vazão de MSG recuperado é positiva, condição "
    "também prevista no Capítulo 5.")

# ---------------------------------------------------------------- 6.3
h2("6.3 DESENVOLVIMENTO DO ALGORITMO")
par("O algoritmo do simulador foi elaborado de modo a reproduzir a sequência lógica dos cálculos realizados "
    "manualmente. Após a leitura dos parâmetros, verifica-se se os valores informados pertencem ao domínio do "
    "modelo. Em caso negativo, o processamento é interrompido e o usuário recebe uma mensagem que identifica "
    "todos os parâmetros inválidos. Em caso afirmativo, executam-se sucessivamente os balanços de massa no "
    "fermentador, no trocador de calor e no separador, seguidos do balanço de energia, da verificação dos "
    "fechamentos e da simulação dos cenários de rendimento. A Figura 2 apresenta o fluxograma do algoritmo.")
figura("Fluxograma do algoritmo do simulador.", fluxo, 11.5)
par("Para facilitar a manutenção e a verificação do código, o software foi dividido em módulos, cada um "
    "responsável por uma parte específica do problema. Essa organização segue o princípio da separação de "
    "responsabilidades: os módulos matemáticos não dependem da interface gráfica e podem ser executados e "
    "testados isoladamente. A estrutura de diretórios do projeto é apresentada no Quadro 1.")
quadro_codigo("Estrutura de diretórios do projeto do simulador.", """
simulador_msg/
├── simulador/                 lógica matemática do modelo
│   ├── parametros.py          parâmetros de entrada e restrições de domínio
│   ├── balanco_massa.py       balanços de massa – Equações (1) a (53)
│   ├── balanco_energia.py     balanço de energia – Equações (54) a (72)
│   └── simulacao.py           integração, cenários e tabelas de resultados
├── tests/
│   └── test_validacao.py      testes automatizados de validação
├── validar.py                 comparação entre resultados analíticos e computacionais
├── app.py                     interface gráfica em Streamlit
└── requirements.txt           bibliotecas e versões utilizadas
""")
par("As responsabilidades de cada módulo, bem como as principais funções implementadas, encontram-se "
    "sintetizadas na Tabela 14.")
tabela("Módulos do simulador e respectivas responsabilidades.",
       ["Módulo", "Principal elemento", "Responsabilidade"],
       [["parametros.py", "ParametrosProcesso", "Armazenar os dados de entrada, calcular grandezas derivadas e validar o domínio"],
        ["balanco_massa.py", "calcular_balanco_massa", "Determinar vazões, composições e resíduos mássicos"],
        ["balanco_energia.py", "calcular_balanco_energia", "Determinar carga térmica, vapor, condensado e resíduo energético"],
        ["simulacao.py", "simular, simular_cenarios", "Integrar os balanços, executar os cenários e montar as tabelas"],
        ["app.py", "—", "Receber os dados do usuário e apresentar resultados e gráficos"],
        ["test_validacao.py", "—", "Verificar automaticamente os resultados de referência"]],
       [2100, 2600, 4371], ["left", "left", "left"])
par("A função principal do algoritmo, denominada *simular*, encadeia as etapas de validação, balanço de massa "
    "e balanço de energia, transmitindo ao balanço de energia as vazões do caldo fermentado e do MSG recuperado "
    "calculadas no balanço de massa. Sua implementação é apresentada no Quadro 2.")
quadro_codigo("Função principal do algoritmo de simulação.", '''
def simular(p: ParametrosProcesso) -> ResultadoSimulacao:
    """Algoritmo principal: valida -> balanço de massa -> balanço de energia."""
    p.validar()
    massa = calcular_balanco_massa(p)
    energia = calcular_balanco_energia(p, m02=massa.totais["02"],
                                       m04=massa.totais["04"])
    return ResultadoSimulacao(p, massa, energia)
''')

# ---------------------------------------------------------------- 6.4
h2("6.4 IMPLEMENTAÇÃO DOS BALANÇOS DE MASSA E ENERGIA EM PYTHON")
par("Os parâmetros de entrada foram implementados por meio de uma classe de dados (*dataclass*) imutável, "
    "denominada ParametrosProcesso, cujos valores padrão correspondem à condição operacional de referência. "
    "A imutabilidade impede que um parâmetro seja alterado inadvertidamente durante a execução dos cálculos, "
    "e a criação de novos cenários é realizada por meio de cópias do objeto original nas quais apenas o "
    "parâmetro de interesse é modificado. As grandezas derivadas foram definidas como propriedades calculadas, "
    "garantindo o atendimento permanente às Equações (4) e (18).")
par("Cada corrente do processo foi representada por um dicionário que associa o nome de cada componente à "
    "respectiva vazão mássica, em kg/h. Essa representação reproduz diretamente a notação ṁ~i,j~ adotada no "
    "Capítulo 4, na qual o índice *i* identifica o componente e o índice *j* identifica a corrente. A vazão "
    "total e as frações mássicas são obtidas por funções auxiliares que implementam as Equações (8) e (9). "
    "Em todo o código, cada linha de cálculo é acompanhada, em comentário, do número da equação correspondente "
    "no relatório, o que permite a conferência direta entre a formulação teórica e sua implementação. O "
    "Quadro 3 apresenta o trecho referente ao fermentador R-101.")
quadro_codigo("Implementação do balanço de massa no fermentador R-101.", '''
# Corrente 01 - Solução açucarada
m_acucar_01 = p.m01 * p.w_acucar_01              # Eq. (12)
m_agua_01 = p.m01 * p.w_agua_01                  # Eq. (13)

# Fermentador R-101
m_acucar_cons = p.X * m_acucar_01                # Eq. (15)
m_acucar_02 = (1.0 - p.X) * m_acucar_01          # Eq. (16)
m_MSG_02 = p.Y_MSG * m_acucar_cons               # Eq. (19)
m_OP_02 = p.Y_OP * m_acucar_cons                 # Eq. (20)
m_agua_02 = m_agua_01                            # Eq. (21)
c02 = {"Água": m_agua_02, "Açúcar": m_acucar_02,
       "MSG": m_MSG_02, "Outros produtos": m_OP_02}
''')
par("No trocador de calor E-101, a corrente 03 é obtida como cópia da corrente 02, em conformidade com as "
    "Equações (27) a (29), que estabelecem a invariância das vazões e composições durante o aquecimento "
    "indireto. No separador S-101, a vazão de MSG recuperado e a parcela não recuperada são calculadas pelas "
    "Equações (33) e (34), enquanto a água, o açúcar residual e os outros produtos são integralmente "
    "direcionados à corrente residual, conforme as Equações (35) a (37). Ao final, o módulo calcula os "
    "resíduos do balanço por equipamento e para o sistema global, segundo as Equações (44) a (48), e os "
    "resíduos por componente, considerando os termos de geração e consumo do fermentador, de acordo com a "
    "Equação (6).")
par("O balanço de energia foi implementado em um módulo independente, que recebe os parâmetros térmicos e as "
    "vazões provenientes do balanço de massa. A relação fundamental, expressa pela Equação (62), permite "
    "calcular a carga térmica e a vazão de vapor; em seguida, determinam-se a potência térmica, a vazão de "
    "condensado, o resíduo energético, o erro relativo e a energia térmica específica por quilograma de MSG "
    "recuperado. O Quadro 4 apresenta a implementação correspondente.")
quadro_codigo("Implementação do balanço de energia no trocador de calor E-101.", '''
delta_T = p.T03 - p.T02                          # Eq. (63)
Q_kJh = m02 * p.cp * delta_T                     # Eq. (62) e (64)
Q_kW = Q_kJh / SEGUNDOS_POR_HORA                 # Eq. (65)
m_U01 = Q_kJh / p.lambda_v                       # Eq. (66)
m_U02 = m_U01                                    # Eq. (60) e (68)

Q_vapor = m_U01 * p.lambda_v                     # Eq. (70)
residuo = Q_vapor - Q_kJh                        # Eq. (69)
erro_relativo = residuo / Q_vapor * 100.0 if Q_vapor > 0 else 0.0   # Eq. (71)
q_MSG = Q_kJh / m04 if m04 > 0 else None         # Eq. (72)
''')
par("Em atendimento à recomendação formulada na Seção 5.7, nenhum resultado intermediário é arredondado. "
    "Todos os cálculos são realizados com a precisão numérica de ponto flutuante de dupla precisão, "
    "aproximadamente quinze a dezesseis algarismos significativos, e o arredondamento é aplicado apenas na "
    "etapa de apresentação dos resultados. Esse procedimento evita a propagação de erros de arredondamento, "
    "como o resíduo de 8 kJ/h observado no Capítulo 5 quando se utiliza a vazão de vapor arredondada.")
par("Por fim, o módulo de simulação organiza os resultados em tabelas do tipo *DataFrame*, da biblioteca "
    "pandas, reproduzindo o formato das Tabelas 6, 7, 8 e 11 do relatório. O mesmo módulo implementa a "
    "simulação dos cenários de rendimento, na qual o rendimento de formação de MSG assume os valores de "
    "0,40; 0,45; 0,50 e 0,55 kg/kg, mantendo-se constantes os demais parâmetros e ajustando-se "
    "complementarmente o rendimento de formação de outros produtos.")

# ---------------------------------------------------------------- 6.5
h2("6.5 DESENVOLVIMENTO DA INTERFACE GRÁFICA EM STREAMLIT")
par("A interface gráfica foi desenvolvida com o objetivo de permitir que o usuário modifique os parâmetros "
    "operacionais e visualize imediatamente os resultados, sem necessidade de interagir com o código-fonte. "
    "O arquivo responsável pela interface não contém nenhuma equação do modelo: sua função restringe-se a "
    "receber os dados, invocar as funções do pacote de cálculo e apresentar os resultados. Essa separação "
    "assegura que a interface utilize exatamente os mesmos cálculos submetidos aos testes de validação.")
par("No Streamlit, o script da aplicação é executado novamente a cada alteração realizada pelo usuário. Assim, "
    "a modificação de qualquer parâmetro gera um novo vetor *p* e uma nova simulação, dispensando o uso de um "
    "botão de cálculo. Os parâmetros de entrada são informados em uma barra lateral, organizada em três grupos: "
    "alimentação e fermentação, separação e aquecimento. Os campos possuem limites mínimos e máximos coerentes "
    "com as restrições da Tabela 13, e um botão permite restaurar a condição operacional de referência.")
par("A área principal apresenta, em destaque, cinco indicadores: vazão de MSG recuperado, vazão de MSG "
    "perdido na corrente residual, potência térmica, consumo de vapor e energia térmica específica. Os "
    "resultados detalhados foram distribuídos em quatro abas, descritas na Tabela 15.")
tabela("Organização das abas da interface gráfica do simulador.",
       ["Aba", "Conteúdo apresentado"],
       [["Balanço de massa", "Vazões e composições mássicas das correntes 01 a 05 (Tabelas 6 e 7) e diagrama de Sankey do fluxo de massa"],
        ["Balanço de energia", "Resultados do trocador E-101 (Tabela 11) e equação fundamental do balanço térmico"],
        ["Verificação", "Resíduos por equipamento, fechamento por componente (Tabela 8) e resíduo energético, com indicação de aprovação"],
        ["Cenários de rendimento", "Tabela comparativa dos quatro rendimentos, gráficos interativos e exportação dos resultados em CSV"]],
       [2400, 6671], ["left", "left"])
par("Caso o usuário informe um valor fora do domínio do modelo, como uma conversão superior à unidade ou uma "
    "temperatura final inferior à inicial, a interface interrompe o cálculo e exibe uma mensagem indicando "
    "quais restrições foram violadas. Os valores numéricos são apresentados no padrão brasileiro, com vírgula "
    "como separador decimal e ponto como separador de milhar. A Figura 3 apresenta a tela inicial do "
    "simulador na condição operacional de referência.")
figura("Tela inicial do simulador na condição operacional de referência.", interface, 15.5)
par("A aplicação é executada localmente por meio do comando *streamlit run app.py*, que inicia um servidor "
    "web no próprio computador e abre o simulador no navegador. Por se tratar de uma aplicação web, o software "
    "pode, futuramente, ser disponibilizado em um servidor para acesso remoto, sem alterações nos módulos de "
    "cálculo.")

# ---------------------------------------------------------------- 6.6
h2("6.6 VALIDAÇÃO DO MODELO COMPUTACIONAL")
par("A validação do modelo computacional teve por objetivo verificar se o software reproduz corretamente as "
    "formulações matemáticas desenvolvidas nos Capítulos 4 e 5. Trata-se, portanto, de uma verificação da "
    "implementação, que compara os resultados computacionais com os resultados analíticos obtidos "
    "manualmente, e não de uma validação experimental frente a dados de uma planta industrial. O procedimento "
    "foi dividido em quatro etapas: comparação com os resultados analíticos na condição de referência, "
    "verificação do fechamento dos balanços, verificação das relações generalizadas para os cenários de "
    "rendimento e verificação do tratamento de entradas inválidas.")
par("Para a comparação entre os valores computacionais e analíticos, definiu-se o desvio relativo percentual "
    "conforme a Equação (75), em que *x*~comp~ corresponde ao valor calculado pelo software e *x*~anal~ ao "
    "valor obtido analiticamente.")
equacao(
    mr("δ") + mr("=", True)
    + mfrac(mdelim(msub(mr("x"), mr("comp", True)) + mr("−", True) + msub(mr("x"), mr("anal", True)), "|", "|"),
            mdelim(msub(mr("x"), mr("anal", True)), "|", "|"))
    + mr("×", True) + mr("100%", True)
)
par("Os resultados dessa comparação, para as principais grandezas dos balanços de massa e de energia na "
    "condição de referência, são apresentados na Tabela 16.")
linhas16 = []
for nome, eq_ref, anal, calc, un in comparacoes:
    casas = 3 if un == "%" else (2 if abs(anal) < 10000 else 0)
    linhas16.append([nome, eq_ref, br(anal, casas), br(calc, casas), un, desvio_txt(calc, anal)])
tabela("Comparação entre os resultados analíticos e computacionais na condição de referência.",
       ["Grandeza", "Eq.", "Analítico", "Computacional", "Unidade", "δ (%)"],
       linhas16, [2500, 650, 1300, 1850, 1100, 1350],
       ["left", "center", "right", "right", "center", "center"])
if desvio_max == 0:
    frase_desvio = ("Todos os desvios relativos são nulos, o que demonstra a correspondência exata entre a "
                    "implementação e a formulação analítica.")
else:
    exp_max = int(f"{desvio_max:e}".split("e")[1]) + 1
    frase_desvio = (f"Os desvios relativos são nulos ou inferiores a {potencia10(exp_max)} %, valores que "
                    "decorrem exclusivamente da representação dos números em ponto flutuante no computador e "
                    "não possuem significado físico. As pequenas diferenças observadas em algumas grandezas "
                    "originam-se de operações como 1 − X e 1 − η, cujos resultados não podem ser "
                    "representados exatamente em base binária.")
par("Verifica-se que os resultados computacionais coincidem com os valores analíticos. " + frase_desvio)
par("Na segunda etapa, avaliou-se o fechamento dos balanços. Considerou-se aprovado o fechamento cujo resíduo, "
    "em valor absoluto, não excede a tolerância numérica τ, conforme a Equação (76).")
equacao(mdelim(mr("ε"), "|", "|") + mr("≤", True) + mr("τ") + mr("=", True) + msup(mr("10", True), mr("−6", True)))
par("Na condição de referência, todos os resíduos de massa por equipamento (R-101, E-101 e S-101), o resíduo "
    "global e os resíduos por componente (água, açúcar, MSG e outros produtos) resultaram iguais a 0 kg/h. O "
    f"resíduo do balanço de energia foi de {br(ee.residuo, 1)} kJ/h, com erro relativo de {br(ee.erro_relativo, 1)} %, "
    "confirmando o fechamento previsto na Seção 5.7. A interface apresenta essa verificação na aba "
    "correspondente, sinalizando ao usuário caso algum resíduo exceda a tolerância.")
par("Na terceira etapa, os resultados de cada cenário de rendimento foram comparados com as relações "
    "generalizadas das Equações (49), (52) e (53), calculadas de forma independente do fluxo principal do "
    "programa. Os resultados constam na Tabela 17.")
linhas17 = [[br(y, 2), br(a4, 2), br(c4, 2), br(a5, 2), br(c5, 2), br(s, 2), br(q, 2)]
            for y, a4, c4, a5, c5, s, q in cenarios]
tabela("Verificação das relações generalizadas para os cenários de rendimento.",
       ["Y_MSG (kg/kg)", "ṁ04 Eq. (49) (kg/h)", "ṁ04 software (kg/h)", "ṁ05 Eq. (52) (kg/h)",
        "ṁ05 software (kg/h)", "ṁ04 + ṁ05 (kg/h)", "Q̇ (kW)"],
       linhas17, [1150, 1350, 1350, 1350, 1350, 1300, 1150], ["center"] * 7)
par("Observa-se a concordância entre as relações analíticas e o software em todos os cenários, bem como o "
    "atendimento à Equação (53), segundo a qual a soma das vazões das correntes 04 e 05 é igual à vazão de "
    "alimentação de 4.000 kg/h. Confirma-se também a conclusão da Seção 5.8: a carga térmica permanece "
    f"constante, em {br(cenarios[0][6], 2)} kW, para os quatro rendimentos, uma vez que a vazão do caldo, o "
    "calor específico e a elevação de temperatura não dependem do rendimento de formação de MSG.")
par("Na quarta etapa, verificou-se o comportamento do software diante de entradas inválidas e de casos-limite. "
    "Foram testados valores negativos de vazão, frações, conversões, rendimentos e eficiências fora do "
    "intervalo entre zero e um, calor específico e calor latente não positivos e temperatura final inferior à "
    "inicial. Em todos os casos, o software rejeitou os dados e informou a restrição violada. Testou-se também "
    "a condição de eficiência de recuperação nula, na qual a vazão de produto é zero, verificando-se que o "
    "programa não incorre em divisão por zero no cálculo das frações mássicas e da energia específica.")
par("As verificações descritas foram implementadas como testes automatizados com o pytest, o que permite "
    "repeti-las integralmente a cada modificação do código. A Tabela 18 resume os testes executados.")
tabela("Resumo dos testes automatizados de validação.",
       ["Grupo de testes", "Referência", "Casos"],
       [["Vazões por componente e corrente", "Tabela 6", "5"],
        ["Composições mássicas e normalização", "Tabela 7 e Eq. (10)", "1"],
        ["Fechamento do balanço de massa", "Tabela 8 e Eq. (44)-(48)", "1"],
        ["Balanço de energia", "Tabela 11", "1"],
        ["Relações generalizadas por cenário", "Eq. (49)-(53)", "4"],
        ["Independência da carga térmica em relação ao rendimento", "Seção 5.8", "1"],
        ["Rejeição de entradas inválidas", "Seções 4.8.3 e 5.8", "8"],
        ["Ausência de divisão por zero", "Eq. (9) e (72)", "1"],
        ["Total", "", str(n_ok + n_falha)]],
       [4700, 3071, 1300], ["left", "left", "center"], negrito_ultima=True)
par(f"Todos os {n_ok} testes foram aprovados" + (f", com {n_falha} falha(s)" if n_falha else ", sem falhas")
    + ". Com base nesses resultados, conclui-se que o modelo computacional reproduz fielmente as formulações "
    "dos balanços de massa e de energia, preserva a conservação de massa e de energia em todas as condições "
    "avaliadas e respeita o domínio de validade estabelecido para o modelo. O simulador encontra-se, portanto, "
    "apto a ser utilizado na análise dos cenários de rendimento apresentada no Capítulo 7.")
par("Ressalta-se que a validação realizada assegura a correção da implementação em relação ao modelo "
    "idealizado, mas não elimina as limitações inerentes às hipóteses simplificadoras adotadas, tais como a "
    "representação da fermentação por rendimentos globais, a separação idealizada sem arraste de componentes, "
    "a restrição do balanço de energia ao trocador de calor e a ausência de perdas térmicas. Essas limitações "
    "serão retomadas na discussão dos resultados.")

doc.save(str(SAIDA))
print("Documento gerado:", SAIDA)
print(f"Testes: {n_ok} aprovados, {n_falha} falhas | desvio máximo: {desvio_max:.2e} %")
