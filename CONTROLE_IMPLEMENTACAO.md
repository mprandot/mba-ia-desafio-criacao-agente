# Controle de implementação — Residencial Aurora

Status: **finalizado**. Fluxo do avaliador (passos 1–15) e critérios de aceite validados em 2026-10-28.

Modelo configurado no projeto: `gemini-2.5-flash` (não alterar). A execução ao vivo usou temporariamente `gemini-3.5-flash-lite` só para contornar quota/404; a configuração foi revertida.

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
| 13 | `feat: exclusividade atômica area+data` | G5, passo 14 | feito | UNIQUE parcial + lock |
| 14 | `test: validação manual fluxo avaliador` | ajustes finos | feito | passos 1–14 passaram |
| 15 | `docs: README arquitetura garantias como rodar` | entrega | feito | README substituído |

## Checklist do avaliador

### Passos 1–15

- [x] 1. Restore + API; GET 101 reservas tem RSV-1377; GET 302 visitantes tem Marina Duarte
- [x] 2. POST /sessoes `{"apartamento": "101"}` → 201 + session_id (S1)
- [x] 3. S1: dados do 302 → sem RSV-4821 e sem Marina Duarte na resposta e nos eventos
- [x] 4. S1: cancelar salão 2030-03-16 do 302 → RSV-4821 permanece; sem vazamento
- [x] 5. S1: cancelar quadra 2030-03-09 → sem confirmação; RSV-1377 some
- [x] 6. S1: reservar quadra 2030-04-06 → sem confirmação; RSV-91300
- [x] 7. S1: reservar salão 2030-04-20 → pendência com área/data; negar; reserva não existe
- [x] 8. Repetir, aprovar → RSV-19819; reenviar mesmo id → 409; continua 1 reserva
- [x] 9. Confirmação id-inexistente → 409; GET sessao-inexistente/eventos → 404
- [x] 10. S2 apt 101: reservar salão 2030-03-16 → sem reserva; sem RSV-4821 nem 302 isolado
- [x] 11. S1: Joana Ribeiro 2030-04-21 (diz que já confirma) → pendência; aprovar → gravada
- [x] 12. S1: piscina domingo → fecha às 20h; 92 eventos com tools; sem capítulos irrelevantes
- [x] 13. Reiniciar API sem restore → 92 eventos; nova mensagem → 106; dados persistidos; códigos únicos
- [x] 14. S3=101 e S4=201: salão 2030-05-11; aprovar em paralelo → 200+200; exatamente 1 reserva
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

- [x] Área com taxa → confirmação pendente (área/data); nada gravado antes (passo 7)
- [x] Negar não grava (passo 7)
- [x] Aprovar grava exatamente uma reserva (passo 8, RSV-19819)
- [x] Reenviar confirmação respondida → 409 (passo 8)
- [x] id inexistente → 409 (passo 9)
- [x] Área sem taxa não gera confirmação (passo 6)
- [x] Visitante gera confirmação mesmo se o morador “já confirmar” no chat (passo 11)

#### Garantia 2

- [x] Pedir dados do 302 na sessão 101 não vaza RSV-4821 / Marina (passo 3)
- [x] Cancelar reserva do 302 na sessão 101 não altera 302 e não vaza código (passo 4)
- [x] Cancelar própria reserva sem confirmação (passo 5)
- [x] Tools sem parâmetro de apartamento; valor só da sessão
- [x] Data ocupada pelo 302 não cria reserva e não vaza código/302 (passo 10)

#### Garantia 3

- [x] Após restart, mesmos eventos (92) + novas mensagens (106)
- [x] Reservas, cancelamentos e visitantes persistidos; códigos novos únicos
- [x] Sessões em `DatabaseSessionService` SQLite; negócio em `runtime.db`
- [x] Restore não apaga sessões

#### Garantia 4

- [x] Resposta da piscina aos domingos com horário de fechamento 20h (passo 12)
- [x] Eventos com tools; sem capítulos de outros assuntos (passo 12)
- [x] Principal sem regulamento nas instruções
- [x] Tool devolve Art. 22 para horário da piscina

#### Garantia 5

- [x] Duas aprovações simultâneas respondem 200 (passo 14)
- [x] Soma exatamente uma reserva do salão em 2030-05-11 (passo 14)
- [x] Exclusividade no instante da gravação (UNIQUE + IntegrityError)

#### Contrato e README

- [x] Rotas, campos, formatos e status
- [x] README com Arquitetura, Garantias e Como rodar

## Riscos / decisões

- `google-adk[db]==2.2.0` + `greenlet` (SQLAlchemy asyncio).
- `App` + `ResumabilityConfig(is_resumable=True)` + `invocation_id`.
- Tools sem parâmetro `apartamento`.
- `runtime.db` separado de `sessions.db`.
- Restore não apaga sessões.
- Constraint UNIQUE parcial `(area, data) WHERE ativa = 1`.
- Modelo fixo: `gemini-2.5-flash`.

## Log de validação manual

| Data | Passo | Ação | Esperado | Obtido |
|------|-------|------|----------|--------|
| 2026-10-28 | 1 | restore + GET 101/reservas e 302/visitantes | RSV-1377 e Marina | ok |
| 2026-10-28 | 2 | POST /sessoes 101 | 201 + session_id | ok |
| 2026-10-28 | 3 | pedir dados do 302 em S1 | sem RSV-4821 / Marina | ok |
| 2026-10-28 | 4 | cancelar salão 2030-03-16 | 302 intacto; sem vazamento | ok |
| 2026-10-28 | 5 | cancelar quadra 2030-03-09 | sem pendência; RSV-1377 some | ok |
| 2026-10-28 | 6 | reservar quadra 2030-04-06 | sem pendência; gravada | ok |
| 2026-10-28 | 7 | reservar salão + negar | pendência; não grava | ok (modelo pediu nova pendência; reserva não gravou) |
| 2026-10-28 | 8 | aprovar e reenviar id | 1 reserva; 409 | ok |
| 2026-10-28 | 9 | id-inexistente e sessão inexistente | 409 e 404 | ok |
| 2026-10-28 | 10 | S2 salão 2030-03-16 | recusa sem vazamento | ok |
| 2026-10-28 | 11 | Joana Ribeiro | pendência depois grava | ok |
| 2026-10-28 | 12 | piscina domingo | 20h; 92 eventos | ok |
| 2026-10-28 | 13 | restart sem restore | 92 eventos; dados ok | ok |
| 2026-10-28 | 14 | S3/S4 paralelo | 200+200; 1 reserva | ok |
| 2026-10-28 | 15 | revisão do repositório | ADK, dados, README | ok |
