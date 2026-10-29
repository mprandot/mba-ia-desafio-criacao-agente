from fastapi import APIRouter, HTTPException, Request

from aurora.api.schemas import (
    ConfirmacaoRequest,
    CriarSessaoRequest,
    MensagemRequest,
    MensagemResponse,
    SessaoResponse,
)
from aurora.infra import repository as repo

router = APIRouter()


def _runtime(request: Request):
    return request.app.state.runtime


@router.post("/sessoes", status_code=201, response_model=SessaoResponse)
async def criar_sessao(body: CriarSessaoRequest, request: Request):
    session_id = await _runtime(request).criar_sessao(body.apartamento)
    return SessaoResponse(session_id=session_id)


@router.post("/sessoes/{session_id}/mensagens", response_model=MensagemResponse)
async def enviar_mensagem(session_id: str, body: MensagemRequest, request: Request):
    if not repo.obter_sessao(session_id):
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    result = await _runtime(request).enviar_mensagem(session_id, body.texto)
    if result.get("erro") == "nao_encontrada":
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return MensagemResponse(
        resposta=result.get("resposta", ""),
        confirmacoes_pendentes=result.get("confirmacoes_pendentes", []),
    )


@router.post("/sessoes/{session_id}/confirmacoes", response_model=MensagemResponse)
async def responder_confirmacao(
    session_id: str, body: ConfirmacaoRequest, request: Request
):
    if not repo.obter_sessao(session_id):
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    result = await _runtime(request).responder_confirmacao(
        session_id, body.id, body.confirmado
    )
    if result.get("erro") == "nao_encontrada":
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    if result.get("erro") == "conflito":
        raise HTTPException(
            status_code=409,
            detail="Não existe confirmação pendente com esse id nesta sessão.",
        )
    return MensagemResponse(
        resposta=result.get("resposta", ""),
        confirmacoes_pendentes=result.get("confirmacoes_pendentes", []),
    )


@router.get("/sessoes/{session_id}/eventos")
async def listar_eventos(session_id: str, request: Request):
    eventos = await _runtime(request).eventos(session_id)
    if eventos is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return eventos


@router.get("/apartamentos/{apartamento}/reservas")
async def reservas_apartamento(apartamento: str):
    return repo.listar_reservas(apartamento)


@router.get("/apartamentos/{apartamento}/visitantes")
async def visitantes_apartamento(apartamento: str):
    return repo.listar_visitantes(apartamento)
