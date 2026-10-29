from google.adk.tools import FunctionTool, ToolContext

from aurora.infra.repository import (
    AreaOcupadaError,
    area_tem_taxa,
    cancelar_reserva_do_apartamento,
    criar_reserva,
    data_disponivel,
    listar_reservas,
    resolver_area_id,
)


def _apartamento(tool_context: ToolContext) -> str:
    apt = tool_context.state.get("apartamento")
    if not apt:
        raise ValueError("Sessão sem apartamento autenticado.")
    return str(apt)


def listar_minhas_reservas(tool_context: ToolContext) -> dict:
    """Lista apenas as reservas ativas do apartamento autenticado nesta sessão."""
    reservas = listar_reservas(_apartamento(tool_context))
    return {"reservas": reservas}


def verificar_disponibilidade(area: str, data: str) -> dict:
    """Informa se a área está livre na data. Não revela quem reservou."""
    area_id = resolver_area_id(area)
    if not area_id:
        return {"erro": "Área não encontrada."}
    return {"area": area_id, "data": data, "disponivel": data_disponivel(area_id, data)}


def cancelar_minha_reserva(
    tool_context: ToolContext,
    area: str | None = None,
    data: str | None = None,
    codigo: str | None = None,
) -> dict:
    """Cancela uma reserva do apartamento autenticado. Não pede confirmação."""
    area_id = resolver_area_id(area) if area else None
    cancelada = cancelar_reserva_do_apartamento(
        _apartamento(tool_context),
        area_id=area_id,
        data=data,
        codigo=codigo,
    )
    if not cancelada:
        return {
            "status": "nao_encontrada",
            "mensagem": "Não há reserva deste apartamento com esses dados.",
        }
    return {"status": "cancelada", "reserva": cancelada}


def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
    """Cria uma reserva para o apartamento autenticado. Área com taxa exige confirmação."""
    area_id = resolver_area_id(area)
    if not area_id:
        return {"erro": "Área não encontrada."}
    if not data_disponivel(area_id, data):
        return {
            "status": "indisponivel",
            "mensagem": "Esta área já está reservada nesta data.",
        }
    try:
        reserva = criar_reserva(_apartamento(tool_context), area_id, data)
    except AreaOcupadaError:
        return {
            "status": "indisponivel",
            "mensagem": "Esta área já está reservada nesta data.",
        }
    return {"status": "reservada", "reserva": reserva}


def _reserva_precisa_confirmacao(area: str, data: str, tool_context: ToolContext) -> bool:
    del data, tool_context
    area_id = resolver_area_id(area)
    return bool(area_id and area_tem_taxa(area_id))


reservar_area_tool = FunctionTool(
    reservar_area,
    require_confirmation=_reserva_precisa_confirmacao,
)

RESERVA_TOOLS = [
    listar_minhas_reservas,
    verificar_disponibilidade,
    cancelar_minha_reserva,
    reservar_area_tool,
]
