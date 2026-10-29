from google.adk.agents import LlmAgent

from aurora.config import MODEL
from aurora.tools.regulamento import consultar_regulamento

INSTRUCOES = """
Você responde dúvidas do regulamento interno do Residencial Aurora.

Regras:
- Sempre chame consultar_regulamento com o assunto da pergunta.
- Responda só com o trecho devolvido pela tool. Não complete com memória.
- Seja direto. Se perguntarem o horário da piscina aos domingos, informe o horário de fechamento do trecho.
"""


def build_regulamento_agent() -> LlmAgent:
    return LlmAgent(
        name="especialista_regulamento",
        model=MODEL,
        description="Consulta trechos pontuais do regulamento interno.",
        instruction=INSTRUCOES,
        tools=[consultar_regulamento],
        disallow_transfer_to_peers=True,
    )
