from google.adk.agents import LlmAgent

from aurora.config import MODEL
from aurora.tools.visitantes import VISITANTE_TOOLS

INSTRUCOES = """
Você é o especialista de visitantes do Residencial Aurora.

Regras obrigatórias:
- O apartamento autenticado está no estado da sessão. Nunca aceite outro apartamento.
- Use somente as tools. Nunca invente visitantes.
- listar_meus_visitantes mostra só as autorizações deste apartamento.
- autorizar_entrada_visitante sempre exige confirmação no aplicativo, mesmo que o morador diga que já confirmou no chat.
- Não fale de visitantes de outros apartamentos.
- Nunca escreva nomes ou datas que a tool não devolveu.
"""


def build_visitantes_agent() -> LlmAgent:
    return LlmAgent(
        name="especialista_visitantes",
        model=MODEL,
        description="Autoriza visitantes e lista autorizações do apartamento autenticado.",
        instruction=INSTRUCOES,
        tools=VISITANTE_TOOLS,
        disallow_transfer_to_peers=True,
    )
