"""ETAPA 3 - Definição dos parâmetros de entrada.

Aqui reunimos TODOS os dados que o usuário pode alterar no simulador.
Os valores padrão correspondem à condição operacional de referência
(Tabela 4 do Capítulo 4 e Tabela 9 do Capítulo 5).

Conceito de Python usado: @dataclass
    Uma dataclass é uma "ficha" com campos nomeados. Ela evita passar
    dez números soltos entre as funções: passamos um único objeto `p`
    e acessamos p.m01, p.X, p.Y_MSG etc.
    frozen=True impede que um valor seja alterado por engano depois de criado.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParametrosProcesso:
    # ---- Balanço de massa (Capítulo 4) ----
    m01: float = 4000.0         # Vazão mássica de alimentação [kg/h]             Eq. (1)
    w_acucar_01: float = 0.20   # Fração mássica de açúcar na alimentação [kg/kg] Eq. (2)
    X: float = 0.80             # Conversão do açúcar [-]                         Eq. (14)
    Y_MSG: float = 0.50         # Rendimento de formação de MSG [kg/kg]           Eq. (19)
    eta_MSG: float = 0.90       # Eficiência de recuperação de MSG [-]            Eq. (32)

    # ---- Balanço de energia (Capítulo 5) ----
    T02: float = 30.0           # Temperatura de entrada do caldo [°C]
    T03: float = 80.0           # Temperatura de saída do caldo [°C]
    cp: float = 4.0             # Calor específico médio do caldo [kJ/(kg·K)]
    lambda_v: float = 2200.0    # Calor latente de condensação do vapor [kJ/kg]

    # Grandezas DERIVADAS: não são digitadas, são calculadas a partir das outras.
    # @property permite usá-las como se fossem campos: p.w_agua_01
    @property
    def w_agua_01(self) -> float:
        """Fração de água na alimentação, pela normalização das frações. Eq. (4)"""
        return 1.0 - self.w_acucar_01

    @property
    def Y_OP(self) -> float:
        """Rendimento de outros produtos, complementar ao de MSG. Eq. (18)"""
        return 1.0 - self.Y_MSG

    def validar(self) -> None:
        """Verifica se os dados estão dentro do domínio do modelo.

        Regras retiradas das Seções 4.8.3 e 5.8:
          - frações, conversão e recuperação entre 0 e 1;
          - rendimentos não negativos e com soma unitária (logo, 0 <= Y_MSG <= 1);
          - vazão não negativa; cp e lambda positivos;
          - temperatura final >= temperatura inicial (somente aquecimento).
        Se houver erro, lança ValueError com TODAS as mensagens de uma vez.
        """
        erros = []
        if self.m01 < 0:
            erros.append("A vazão de alimentação (m01) não pode ser negativa.")
        if not 0.0 <= self.w_acucar_01 <= 1.0:
            erros.append("A fração de açúcar (w_açúcar,01) deve estar entre 0 e 1.")
        if not 0.0 <= self.X <= 1.0:
            erros.append("A conversão (X) deve estar entre 0 e 1.")
        if not 0.0 <= self.Y_MSG <= 1.0:
            erros.append("O rendimento de MSG (Y_MSG) deve estar entre 0 e 1, pois Y_MSG + Y_OP = 1.")
        if not 0.0 <= self.eta_MSG <= 1.0:
            erros.append("A eficiência de recuperação (η_MSG) deve estar entre 0 e 1.")
        if self.cp <= 0:
            erros.append("O calor específico (cp) deve ser positivo.")
        if self.lambda_v <= 0:
            erros.append("O calor latente (λv) deve ser positivo.")
        if self.T03 < self.T02:
            erros.append("A temperatura final (T03) deve ser maior ou igual à inicial (T02).")
        if erros:
            raise ValueError("\n".join(erros))
