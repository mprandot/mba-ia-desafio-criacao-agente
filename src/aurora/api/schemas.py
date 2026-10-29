from pydantic import BaseModel, Field


class CriarSessaoRequest(BaseModel):
    apartamento: str


class SessaoResponse(BaseModel):
    session_id: str


class MensagemRequest(BaseModel):
    texto: str


class ConfirmacaoPendente(BaseModel):
    id: str
    acao: str
    detalhes: dict = Field(default_factory=dict)


class MensagemResponse(BaseModel):
    resposta: str
    confirmacoes_pendentes: list[ConfirmacaoPendente] = Field(default_factory=list)


class ConfirmacaoRequest(BaseModel):
    id: str
    confirmado: bool
