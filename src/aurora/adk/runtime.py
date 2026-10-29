from __future__ import annotations

import json
from typing import Any

from google.adk.apps import App, ResumabilityConfig
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from aurora.agents import build_root_agent
from aurora.config import APP_NAME, SESSIONS_DB, ensure_runtime_dir
from aurora.infra import repository as repo

CONFIRMATION_TOOL = "adk_request_confirmation"


class AuroraRuntime:
    def __init__(self) -> None:
        ensure_runtime_dir()
        repo.init_db()
        self.session_service = DatabaseSessionService(
            f"sqlite+aiosqlite:///{SESSIONS_DB.as_posix()}"
        )
        self.app = App(
            name=APP_NAME,
            root_agent=build_root_agent(),
            resumability_config=ResumabilityConfig(is_resumable=True),
        )
        self.runner = Runner(app=self.app, session_service=self.session_service)

    async def prepare(self) -> None:
        if hasattr(self.session_service, "prepare_tables"):
            await self.session_service.prepare_tables()

    async def close(self) -> None:
        close = getattr(self.session_service, "close", None)
        if close:
            result = close()
            if hasattr(result, "__await__"):
                await result

    async def criar_sessao(self, apartamento: str) -> str:
        session = await self.session_service.create_session(
            app_name=APP_NAME,
            user_id=apartamento,
            state={"apartamento": apartamento},
        )
        repo.salvar_sessao(session.id, apartamento, apartamento)
        return session.id

    async def obter_sessao_adk(self, session_id: str):
        meta = repo.obter_sessao(session_id)
        if not meta:
            return None
        return await self.session_service.get_session(
            app_name=APP_NAME,
            user_id=meta["user_id"],
            session_id=session_id,
        )

    async def enviar_mensagem(self, session_id: str, texto: str) -> dict:
        meta = repo.obter_sessao(session_id)
        if not meta:
            return {"erro": "nao_encontrada"}
        message = types.Content(
            role="user",
            parts=[types.Part.from_text(text=texto)],
        )
        return await self._rodar(
            user_id=meta["user_id"],
            session_id=session_id,
            new_message=message,
        )

    async def responder_confirmacao(
        self,
        session_id: str,
        confirmation_id: str,
        confirmado: bool,
    ) -> dict:
        meta = repo.obter_sessao(session_id)
        if not meta:
            return {"erro": "nao_encontrada"}
        pendencia = repo.obter_confirmacao(session_id, confirmation_id)
        if not pendencia or pendencia["respondida"]:
            return {"erro": "conflito"}
        if not repo.marcar_confirmacao_respondida(session_id, confirmation_id):
            return {"erro": "conflito"}

        message = types.Content(
            role="user",
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=pendencia["function_call_id"],
                        name=CONFIRMATION_TOOL,
                        response={"confirmed": confirmado},
                    )
                )
            ],
        )
        kwargs: dict[str, Any] = {
            "user_id": meta["user_id"],
            "session_id": session_id,
            "new_message": message,
        }
        if pendencia.get("invocation_id"):
            kwargs["invocation_id"] = pendencia["invocation_id"]
        return await self._rodar(**kwargs)

    async def eventos(self, session_id: str) -> list[dict] | None:
        session = await self.obter_sessao_adk(session_id)
        if not session:
            return None
        saida = []
        for event in session.events or []:
            saida.append(_serializar_evento(event))
        return saida

    async def _rodar(self, **kwargs) -> dict:
        textos: list[str] = []
        async for event in self.runner.run_async(**kwargs):
            self._capturar_confirmacoes(kwargs["session_id"], event)
            textos.extend(_textos_do_evento(event))
        await self._sincronizar_confirmacoes(kwargs["session_id"])
        return {
            "resposta": "\n".join(textos).strip(),
            "confirmacoes_pendentes": repo.listar_confirmacoes_pendentes(
                kwargs["session_id"]
            ),
        }

    async def _sincronizar_confirmacoes(self, session_id: str) -> None:
        session = await self.obter_sessao_adk(session_id)
        if not session:
            return
        for event in session.events or []:
            self._capturar_confirmacoes(session_id, event)

    def _capturar_confirmacoes(self, session_id: str, event: Any) -> None:
        invocation_id = getattr(event, "invocation_id", "") or ""
        calls = []
        if hasattr(event, "get_function_calls"):
            calls = event.get_function_calls() or []
        else:
            content = getattr(event, "content", None)
            if content and getattr(content, "parts", None):
                calls = [
                    part.function_call
                    for part in content.parts
                    if getattr(part, "function_call", None)
                ]
        for fc in calls:
            if getattr(fc, "name", None) != CONFIRMATION_TOOL:
                continue
            args = _args_dict(fc)
            detalhes, acao = _detalhes_da_confirmacao(args)
            repo.upsert_confirmacao(
                confirmation_id=fc.id,
                session_id=session_id,
                function_call_id=fc.id,
                invocation_id=invocation_id,
                acao=acao,
                detalhes=detalhes,
            )


def _args_dict(fc: Any) -> dict:
    args = getattr(fc, "args", None) or {}
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {"raw": args}
    if isinstance(args, dict):
        return args
    return {}


def _detalhes_da_confirmacao(args: dict) -> tuple[dict, str]:
    original = args.get("originalFunctionCall") or args.get(
        "original_function_call"
    )
    if isinstance(original, dict):
        inner_args = original.get("args") or {}
        nome_tool = original.get("name") or ""
    else:
        payload = args.get("payload") if isinstance(args.get("payload"), dict) else {}
        inner_args = (
            payload.get("args")
            or args.get("args")
            or {}
        )
        nome_tool = payload.get("name") or args.get("hint") or ""
    if not isinstance(inner_args, dict):
        inner_args = {}
    detalhes: dict[str, Any] = {}
    for chave in ("area", "data", "nome"):
        if inner_args.get(chave):
            detalhes[chave] = inner_args[chave]
    if "area" in detalhes:
        from aurora.infra.repository import resolver_area_id

        resolved = resolver_area_id(str(detalhes["area"]))
        if resolved:
            detalhes["area"] = resolved
    acao = "autorizar_visitante" if "nome" in detalhes else "reservar_area"
    if isinstance(nome_tool, str) and "visit" in nome_tool.lower():
        acao = "autorizar_visitante"
    return detalhes, acao


def _textos_do_evento(event: Any) -> list[str]:
    content = getattr(event, "content", None)
    if not content or not getattr(content, "parts", None):
        return []
    textos = []
    for part in content.parts:
        text = getattr(part, "text", None)
        if text:
            textos.append(text)
    return textos


def _serializar_evento(event: Any) -> dict:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    if hasattr(event, "dict"):
        return event.dict()
    return {"repr": repr(event)}
