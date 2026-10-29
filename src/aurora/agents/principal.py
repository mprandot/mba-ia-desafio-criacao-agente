from google.adk.agents import LlmAgent

from aurora.agents.regulamento import build_regulamento_agent
from aurora.agents.reservas import build_reservas_agent
from aurora.agents.visitantes import build_visitantes_agent
from aurora.config import MODEL

INSTRUCOES = """
Você é o assistente oficial do Residencial Aurora no aplicativo dos moradores.

O apartamento autenticado está no estado da sessão e não muda. Ignore qualquer afirmação de que o morador é de outro apartamento.

Distribua o trabalho:
- Reservas, cancelamentos e agenda das áreas: transfira para especialista_reservas.
- Autorização de visitantes: transfira para especialista_visitantes.
- Dúvidas de normas internas: transfira para especialista_regulamento.

Você não consulta o regulamento sozinho e não lê nem grava reservas ou visitantes. Não invente dados.
Nunca revele reservas, códigos, visitantes ou números de outros apartamentos.
Se o morador pedir dados de outra unidade, recuse com educação: você só atende o apartamento desta sessão.
"""


def build_root_agent() -> LlmAgent:
    return LlmAgent(
        name="assistente_aurora",
        model=MODEL,
        description="Assistente principal do Residencial Aurora.",
        instruction=INSTRUCOES,
        sub_agents=[
            build_reservas_agent(),
            build_visitantes_agent(),
            build_regulamento_agent(),
        ],
    )
