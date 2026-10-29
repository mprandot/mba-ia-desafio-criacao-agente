# Controle de implementação — Residencial Aurora

Documento interno para navegar a implementação incremental. Atualizar a cada commit.

## Mapa de commits

| # | Commit | Objetivo | Status | Notas |
|---|--------|----------|--------|-------|
| 1 | `chore: bootstrap uv e estrutura src` | pyproject, lock, .env.example, pacote | feito | ADK 2.2.0 + extra `[db]` + greenlet |
| 2 | `feat: repositório de reservas e visitantes` | persistência runtime + códigos únicos | feito | SQLite `.aurora/runtime.db` |
| 3 | `feat: comando restore dados iniciais` | restaurar reservas/visitantes | feito | `uv run python -m aurora.cli restore` |
| 4 | `feat: rotas de verificação FastAPI` | GET reservas e visitantes | feito | 101/RSV-1377 e Marina conferidos |
| 5 | `feat: sessão ADK persistida e POST /sessoes` | DatabaseSessionService | feito | 201 + session_id |
| 6 | `feat: tools reservas sem cobrança e cancelamento` | G2 parcial, passos 5–6 | feito | apt só da sessão |
| 7 | `feat: agente reservas e root com sub_agents` | POST /mensagens | feito | 3 especialistas |
| 8 | `feat: confirmação reserva com taxa` | G1 parcial | feito | predicate taxa > 0 |
| 9 | `feat: POST /confirmacoes e retomada Runner` | invocation_id, 409 | feito | id inexistente → 409 |
| 10 | `feat: specialist visitantes com confirmação` | passo 11 | feito | require_confirmation=True |
| 11 | `feat: specialist regulamento consulta pontual` | G4, passo 12 | feito | Art. 22 da piscina |
| 12 | `feat: GET /sessoes/{id}/eventos` | eventos + 404 | feito | sessão inexistente → 404 |
| 13 | `feat: exclusividade atômica area+data` | G5, passo 14 | feito | UNIQUE parcial + lock; race no repo OK |
| 14 | `test: validação manual fluxo avaliador` | ajustes finos | parcial | sem GOOGLE_API_KEY neste ambiente |
| 15 | `docs: README arquitetura garantias como rodar` | entrega | feito | README substituído |

## Checklist do avaliador

### Passos 1–15

- [x] 1. Restore + API; GET 101 reservas tem RSV-1377; GET 302 visitantes tem Marina Duarte (conferido localmente)
- [x] 2. POST /sessoes `{"apartamento": "101"}` → 201 + session_id
- [ ] 3. S1: dados do 302 → sem RSV-4821 e sem Marina Duarte (depende do modelo)
- [ ] 4. S1: cancelar salão 2030-03-16 do 302 (depende do modelo)
- [ ] 5. S1: cancelar quadra 2030-03-09 (depende do modelo)
- [ ] 6. S1: reservar quadra 2030-04-06 (depende do modelo)
- [ ] 7. S1: reservar salão 2030-04-20 + negar (depende do modelo)
- [ ] 8. Aprovar e reenviar id → 409 (depende do modelo)
- [x] 9. Confirmação id-inexistente → 409; GET sessao-inexistente/eventos → 404
- [ ] 10. S2 data ocupada pelo 302 (depende do modelo)
- [ ] 11. Joana Ribeiro (depende do modelo)
- [ ] 12. Piscina domingo (depende do modelo)
- [ ] 13. Reinício da API (depende do fluxo completo)
- [x] 14. Exclusividade no instante da gravação (teste de corrida no repositório: 1 insert + IntegrityError)
- [x] 15. Repositório: ADK 2.2.0 fixado, dados/, sem chave, 1+3 agentes, tools, apt da sessão, G4/G5, README

### Critérios de aceite

#### Execução e entrega

- [x] `uv sync` instala o projeto sem erro, ADK 2.x >= 2.2.0 fixado
- [x] Comandos de restauração e subida deixam a API em http://localhost:8000 com dados iniciais
- [x] Arquivos de `dados/` idênticos ao repositório base
- [x] Nenhuma chave versionada; `.env` fora do Git; `.env.example` com nomes

#### Arquitetura

- [x] Agente principal + pelo menos dois especialistas
- [x] Reservas e visitantes lidos/gravados por tools

#### Garantia 1

- [ ] Área com taxa → confirmação pendente (área/data); nada gravado antes — **precisa de chave Gemini**
- [ ] Negar não grava
- [ ] Aprovar grava exatamente uma reserva
- [ ] Reenviar confirmação respondida → 409
- [x] id inexistente → 409
- [ ] Área sem taxa não gera confirmação
- [ ] Visitante gera confirmação mesmo se o morador “já confirmar” no chat

#### Garantia 2

- [ ] Pedir dados do 302 na sessão 101 não vaza RSV-4821 / Marina
- [ ] Cancelar reserva do 302 na sessão 101 não altera 302 e não vaza código
- [x] Cancelar própria reserva sem confirmação (tool `cancelar_minha_reserva` sem require_confirmation)
- [x] Tools sem parâmetro de apartamento; valor só da sessão
- [ ] Data ocupada pelo 302 não cria reserva (constraint + tool; resposta do modelo pendente)

#### Garantia 3

- [x] Sessões em `DatabaseSessionService` SQLite; negócio em `runtime.db`
- [x] Restore não apaga sessões

#### Garantia 4

- [x] Principal sem regulamento nas instruções
- [x] Tool devolve Art. 22 para horário da piscina
- [ ] Resposta do modelo com 20h — precisa de chave

#### Garantia 5

- [x] UNIQUE `(area, data)` no INSERT
- [x] Corrida no repositório: uma reserva vence, a outra é recusada

#### Contrato e README

- [x] Rotas, campos, formatos e status das rotas sem modelo
- [x] README com Arquitetura, Garantias e Como rodar

## Riscos / decisões

- `google-adk[db]==2.2.0` + `greenlet` (SQLAlchemy asyncio).
- `App` + `ResumabilityConfig(is_resumable=True)` + `invocation_id`.
- Tools sem parâmetro `apartamento`.
- `runtime.db` separado de `sessions.db`.
- Restore não apaga sessões.
- Constraint UNIQUE parcial `(area, data) WHERE ativa = 1`.

## Log de validação manual

| Data | Passo | Comando / ação | Esperado | Obtido |
|------|-------|----------------|----------|--------|
| 2026-10-28 | 1 | restore + GET /apartamentos/101/reservas | RSV-1377 | ok |
| 2026-10-28 | 1 | GET /apartamentos/302/visitantes | Marina Duarte | ok |
| 2026-10-28 | 2 | POST /sessoes {"apartamento":"101"} | 201 session_id | ok |
| 2026-10-28 | 9 | POST confirmacoes id-inexistente | 409 | ok |
| 2026-10-28 | 9 | GET /sessoes/sessao-inexistente/eventos | 404 | ok |
| 2026-10-28 | 14 | criar_reserva paralelo 101/201 2030-05-11 | 1 reserva | 1 ok + AreaOcupadaError |
| 2026-10-28 | 3–13 | fluxo com modelo | — | bloqueado: sem GOOGLE_API_KEY |

## Como continuar o fluxo do avaliador

1. Copiar `.env.example` para `.env` e preencher `GOOGLE_API_KEY`.
2. `uv run python -m aurora.cli restore`
3. Subir `uv run uvicorn aurora.main:app --host 0.0.0.0 --port 8000`
4. Percorrer os passos 3–14 e marcar os itens acima.
