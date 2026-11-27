# Simulador do processo de produção de MSG — guia passo a passo

Simulador em Python/Streamlit dos balanços de massa (Capítulo 4) e de energia
(Capítulo 5) do processo simplificado de produção de glutamato monossódico:

```
01 Solução açucarada → [R-101 Fermentador] → 02 → [E-101 Trocador] → 03 → [S-101 Separador] → 04 MSG recuperado
                                                     ↑ U01 vapor  ↓ U02 condensado                  ↘ 05 Corrente residual
```

---

## Etapa 1 — Ambiente de desenvolvimento

| Ferramenta | Versão usada | Para quê |
|---|---|---|
| Python | 3.13.2 | Executar os cálculos |
| VS Code + extensões Python e Pylance | — | Editar e rodar o código |
| Streamlit | 1.67.0 | Interface gráfica |
| pandas | 3.1.1 | Tabelas de resultados |
| Plotly | 7.2.0 | Gráficos interativos |
| pytest | 9.2.0 | Testes de validação |

> No seu computador, o comando `python` não está no PATH (o Windows abre a Microsoft Store).
> Use o lançador **`py`** no lugar: `py --version`. Dentro do ambiente virtual, `python` funciona normalmente.

## Etapa 2 — Estrutura do projeto

```
simulador_msg/
├── .venv/                  ambiente virtual (bibliotecas isoladas deste projeto)
├── simulador/              LÓGICA MATEMÁTICA (sem interface)
│   ├── parametros.py       Etapa 3 – dados de entrada e validação
│   ├── balanco_massa.py    Etapa 4 – Eq. (1) a (53)
│   ├── balanco_energia.py  Etapa 5 – Eq. (54) a (72)
│   └── simulacao.py        Etapas 8–9 – integração, cenários e tabelas
├── tests/test_validacao.py Etapa 6 – testes automáticos
├── validar.py              Etapa 6 – tabela analítico × computacional
├── app.py                  Etapa 7 – interface Streamlit
├── docs/                   gerador do Capítulo 6 (.docx) e figuras
└── requirements.txt        lista de bibliotecas
```

Como o ambiente foi criado (PowerShell, dentro da pasta do projeto):

```powershell
py -3.13 -m venv .venv                       # cria o ambiente virtual
.\.venv\Scripts\Activate.ps1                 # ativa (aparece (.venv) no início da linha)
python -m pip install -r requirements-dev.txt   # instala as bibliotecas (app + testes + docs)
```

Se o PowerShell bloquear o `Activate.ps1`, execute uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

No VS Code: **File → Open Folder** → `simulador_msg`, depois `Ctrl+Shift+P` →
*Python: Select Interpreter* → escolha o que está em `.venv`.

## Etapa 3 — Parâmetros de entrada (`simulador/parametros.py`)

Todos os dados ficam em uma `dataclass` chamada `ParametrosProcesso`, já com os
valores da condição de referência (m₀₁ = 4000 kg/h, w = 0,20, X = 0,80,
Y_MSG = 0,50, η = 0,90, 30→80 °C, cp = 4,0, λ = 2200). O método `validar()`
aplica as restrições de domínio das Seções 4.8.3 e 5.8.

**Experimente** (com o ambiente ativado):

```powershell
python -c "from simulador.parametros import ParametrosProcesso as P; p=P(); print(p, p.Y_OP)"
python -c "from simulador.parametros import ParametrosProcesso as P; P(X=1.5).validar()"
```

## Etapa 4 — Balanços de massa (`simulador/balanco_massa.py`)

Cada corrente é um dicionário `{componente: vazão}`. As linhas de cálculo trazem
o número da equação do relatório, por exemplo:

```python
m_acucar_cons = p.X * m_acucar_01          # Eq. (15)
m_MSG_02 = p.Y_MSG * m_acucar_cons         # Eq. (19)
```

## Etapa 5 — Balanços de energia (`simulador/balanco_energia.py`)

Implementa a Eq. (62): `Q = m02·cp·(T03 − T02) = mU01·λv`, a conversão para kW,
o vapor, o resíduo energético e a energia específica por kg de MSG. Nenhum
valor é arredondado internamente (recomendação da Seção 5.7).

## Etapa 6 — Validação matemática

```powershell
python -m pytest -v      # 22 testes: Tabelas 6, 7, 8, 11, Eq. (49)-(53) e domínio
python validar.py        # tabela "analítico × computacional" usada na Seção 6.6
```

## Etapa 7 — Interface gráfica

```powershell
streamlit run app.py     # abre http://localhost:8501
```

Barra lateral = entradas; abas = balanço de massa, balanço de energia,
verificação dos fechamentos e cenários. Toda alteração recalcula na hora.
Para encerrar, `Ctrl+C` no terminal.

## Etapas 8 e 9 — Cenários, tabelas e gráficos

A aba **Cenários de rendimento** roda Y_MSG = 0,40; 0,45; 0,50 e 0,55 mantendo os
demais parâmetros, e mostra tabela, quatro gráficos e botão para baixar CSV.

| Y_MSG | MSG formado | MSG recuperado (04) | MSG perdido | Carga térmica | Energia específica |
|---|---|---|---|---|---|
| 0,40 | 256,0 kg/h | 230,4 kg/h | 25,6 kg/h | 222,22 kW | 3 472,2 kJ/kg |
| 0,45 | 288,0 kg/h | 259,2 kg/h | 28,8 kg/h | 222,22 kW | 3 086,4 kJ/kg |
| 0,50 | 320,0 kg/h | 288,0 kg/h | 32,0 kg/h | 222,22 kW | 2 777,8 kJ/kg |
| 0,55 | 352,0 kg/h | 316,8 kg/h | 35,2 kg/h | 222,22 kW | 2 525,3 kJ/kg |

## Etapa 10 — Finalização

Checklist: testes passando (`pytest`), app abrindo sem erros, valores de
referência conferidos com as Tabelas 6, 7, 8 e 11. O Capítulo 6 do relatório
é gerado por `python docs/gerar_capitulo6.py`.

### Exercícios para fixar

1. Altere a conversão para X = 0,90 e preveja (à mão) o novo m₀₄ antes de olhar o app.
2. Coloque T₀₃ = 70 °C: o que acontece com o vapor? E com os resultados de massa? Por quê?
3. Adicione ao `simular_cenarios` uma coluna "Açúcar residual (kg/h)" e exiba-a na tabela.
4. Escreva um teste novo em `tests/test_validacao.py` para o caso η_MSG = 1,0 (sem perdas).
