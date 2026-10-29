# Assistente virtual do Residencial Aurora

API do assistente do condomínio, construída com Google ADK 2.2.0 e FastAPI. O modelo conduz a conversa; as regras críticas ficam no código.

## Arquitetura

O morador fala com o agente principal `assistente_aurora` ([`src/aurora/agents/principal.py`](src/aurora/agents/principal.py)). Ele não lê nem grava dados e não recebe o regulamento: só encaminha o pedido a um especialista.

| Agente | Arquivo | Como é acionado | Por quê |
|--------|---------|-----------------|---------|
| `assistente_aurora` | [`principal.py`](src/aurora/agents/principal.py) | Root do `App` | Ponto único de entrada; isola o morador das tools |
| `especialista_reservas` | [`reservas.py`](src/aurora/agents/reservas.py) | `sub_agents` + transferência | Reservas, cancelamentos e agenda |
| `especialista_visitantes` | [`visitantes.py`](src/aurora/agents/visitantes.py) | `sub_agents` + transferência | Autorização de entrada com confirmação |
| `especialista_regulamento` | [`regulamento.py`](src/aurora/agents/regulamento.py) | `sub_agents` + transferência | Consulta pontual do regulamento, fora do contexto do principal |

Reservas e visitantes só passam pelas tools em [`src/aurora/tools/reservas.py`](src/aurora/tools/reservas.py) e [`src/aurora/tools/visitantes.py`](src/aurora/tools/visitantes.py). O estado de negócio fica em `.aurora/runtime.db`; as sessões ADK ficam em `.aurora/sessions.db`.

A API em [`src/aurora/api/routes.py`](src/aurora/api/routes.py) expõe conversa, confirmações, eventos e rotas de verificação. O `Runner` e o `App` resumível estão em [`src/aurora/adk/runtime.py`](src/aurora/adk/runtime.py).

```text
POST /sessoes  →  DatabaseSessionService (apartamento no state)
POST /mensagens  →  Runner.run_async
POST /confirmacoes  →  FunctionResponse adk_request_confirmation + invocation_id
GET  /eventos  →  eventos persistidos da sessão
GET  /apartamentos/{apt}/reservas|visitantes  →  SQLite, sem modelo
```

## Garantias

### Garantia 1 — cobrança ou acesso só com confirmação

- Reserva com taxa: `FunctionTool(..., require_confirmation=_reserva_precisa_confirmacao)` em [`src/aurora/tools/reservas.py`](src/aurora/tools/reservas.py).
- Visitante: `FunctionTool(..., require_confirmation=True)` em [`src/aurora/tools/visitantes.py`](src/aurora/tools/visitantes.py).
- A API extrai `adk_request_confirmation` dos eventos e devolve `confirmacoes_pendentes` ([`src/aurora/adk/runtime.py`](src/aurora/adk/runtime.py)).
- Aprovar ou negar só vale em `POST /sessoes/{id}/confirmacoes`. Id inexistente ou já respondido retorna 409; a marca `respondida` é atômica em [`src/aurora/infra/repository.py`](src/aurora/infra/repository.py) (`marcar_confirmacao_respondida`).
- A retomada envia `FunctionResponse` com o mesmo `function_call_id` e o `invocation_id` da pendência.

### Garantia 2 — cada sessão pertence a um apartamento

- O apartamento é gravado uma vez em `create_session(..., state={"apartamento": ...})` em [`src/aurora/adk/runtime.py`](src/aurora/adk/runtime.py).
- Nenhuma tool aceita apartamento escolhido pelo modelo. `_apartamento(tool_context)` lê só `tool_context.state["apartamento"]` em [`src/aurora/tools/reservas.py`](src/aurora/tools/reservas.py) e [`src/aurora/tools/visitantes.py`](src/aurora/tools/visitantes.py).
- `verificar_disponibilidade` devolve apenas `{disponivel: true|false}`. Cancelamento de outra unidade não encontra a reserva e não vaza o código.

### Garantia 3 — nada se perde no reinício

- Sessões e eventos: `DatabaseSessionService("sqlite+aiosqlite:///.aurora/sessions.db")` em [`src/aurora/adk/runtime.py`](src/aurora/adk/runtime.py).
- Reservas, visitantes e pendências: SQLite em `.aurora/runtime.db` ([`src/aurora/infra/repository.py`](src/aurora/infra/repository.py)).
- O restore não apaga `sessions.db`.

### Garantia 4 — o regulamento é consultado, não carregado

- O principal não inclui o regulamento nas instruções ([`src/aurora/agents/principal.py`](src/aurora/agents/principal.py)).
- `consultar_regulamento` em [`src/aurora/tools/regulamento.py`](src/aurora/tools/regulamento.py) devolve só o artigo ou capítulo pedido (ex.: Art. 22 para horário da piscina).

### Garantia 5 — dois moradores, uma reserva

- Índice único parcial `UNIQUE (area, data) WHERE ativa = 1` em [`src/aurora/infra/repository.py`](src/aurora/infra/repository.py).
- `criar_reserva` faz o `INSERT` sob lock e trata `IntegrityError` como data ocupada, sem erro HTTP. A exclusividade vale no instante da gravação.

## Como rodar

Pré-requisitos: Python 3.12+, [uv](https://docs.astral.sh/uv/), chave do Google AI Studio.

```bash
cp .env.example .env
# preencha GOOGLE_API_KEY
uv sync
uv run python -m aurora.cli restore
uv run uvicorn aurora.main:app --host 0.0.0.0 --port 8000
```

A API fica em `http://localhost:8000`.

### Variáveis do `.env`

| Variável | Uso |
|----------|-----|
| `GOOGLE_API_KEY` | Chave do Google AI Studio |
| `GOOGLE_GENAI_USE_VERTEXAI` | `FALSE` para AI Studio |
| `AURORA_MODEL` | Modelo Gemini (padrão `gemini-2.5-flash`) |

### Restaurar dados

`uv run python -m aurora.cli restore` recarrega reservas e visitantes a partir de `dados/` (arquivos de seed não são alterados). Sessões ADK são preservadas.

Os arquivos em `dados/` são o estado inicial do condomínio e permanecem idênticos ao repositório base.
