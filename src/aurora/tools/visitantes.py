from google.adk.tools import FunctionTool, ToolContext

from aurora.infra.repository import autorizar_visitante, listar_visitantes


def _apartamento(tool_context: ToolContext) -> str:
    apt = tool_context.state.get("apartamento")
    if not apt:
        raise ValueError("Sessão sem apartamento autenticado.")
    return str(apt)


def listar_meus_visitantes(tool_context: ToolContext) -> dict:
    """Lista apenas as autorizações de visita do apartamento autenticado."""
    return {"visitantes": listar_visitantes(_apartamento(tool_context))}


def autorizar_entrada_visitante(
    nome: str, data: str, tool_context: ToolContext
) -> dict:
    """Autoriza a entrada de um visitante. Sempre exige confirmação pela rota da API."""
    registro = autorizar_visitante(_apartamento(tool_context), nome, data)
    return {"status": "autorizado", "visitante": registro}


autorizar_entrada_tool = FunctionTool(
    autorizar_entrada_visitante,
    require_confirmation=True,
)

VISITANTE_TOOLS = [
    listar_meus_visitantes,
    autorizar_entrada_tool,
]
