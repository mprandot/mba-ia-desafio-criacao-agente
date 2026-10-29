from __future__ import annotations

import json
import random
import sqlite3
import threading
from pathlib import Path

from aurora.config import DADOS_DIR, RUNTIME_DB, ensure_runtime_dir

_lock = threading.Lock()


class AreaOcupadaError(Exception):
    """A área já tem reserva ativa na data."""


def _connect() -> sqlite3.Connection:
    ensure_runtime_dir()
    conn = sqlite3.connect(RUNTIME_DB, timeout=30, isolation_level="DEFERRED")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db() -> None:
    with _lock:
        conn = _connect()
        try:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS areas (
                    id TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    taxa REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS apartamentos (
                    numero TEXT PRIMARY KEY,
                    morador TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reservas (
                    codigo TEXT PRIMARY KEY,
                    apartamento TEXT NOT NULL,
                    area TEXT NOT NULL,
                    data TEXT NOT NULL,
                    ativa INTEGER NOT NULL DEFAULT 1
                );
                CREATE UNIQUE INDEX IF NOT EXISTS ux_reserva_ativa
                    ON reservas(area, data) WHERE ativa = 1;
                CREATE TABLE IF NOT EXISTS visitantes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    apartamento TEXT NOT NULL,
                    nome TEXT NOT NULL,
                    data TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessoes (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    apartamento TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS confirmacoes (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    function_call_id TEXT NOT NULL,
                    invocation_id TEXT NOT NULL,
                    acao TEXT NOT NULL,
                    detalhes TEXT NOT NULL,
                    respondida INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            conn.commit()
        finally:
            conn.close()


def restore() -> None:
    init_db()
    with _lock:
        conn = _connect()
        try:
            conn.execute("DELETE FROM reservas")
            conn.execute("DELETE FROM visitantes")
            conn.execute("DELETE FROM areas")
            conn.execute("DELETE FROM apartamentos")
            conn.execute("DELETE FROM confirmacoes")

            areas = _read_json("areas.json")
            for area in areas:
                conn.execute(
                    "INSERT INTO areas (id, nome, taxa) VALUES (?, ?, ?)",
                    (area["id"], area["nome"], area["taxa"]),
                )

            apts = _read_json("apartamentos.json")
            for apt in apts:
                conn.execute(
                    "INSERT INTO apartamentos (numero, morador) VALUES (?, ?)",
                    (apt["numero"], apt["morador"]),
                )

            reservas = _read_json("reservas.json")
            for reserva in reservas:
                conn.execute(
                    """
                    INSERT INTO reservas (codigo, apartamento, area, data, ativa)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (
                        reserva["codigo"],
                        reserva["apartamento"],
                        reserva["area"],
                        reserva["data"],
                    ),
                )

            visitantes = _read_json("visitantes.json")
            for visitante in visitantes:
                conn.execute(
                    """
                    INSERT INTO visitantes (apartamento, nome, data)
                    VALUES (?, ?, ?)
                    """,
                    (
                        visitante["apartamento"],
                        visitante["nome"],
                        visitante["data"],
                    ),
                )
            conn.commit()
        finally:
            conn.close()


def _read_json(name: str) -> list:
    path = DADOS_DIR / name
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get_area(area_id: str) -> dict | None:
    init_db()
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM areas WHERE id = ?", (area_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def find_area_by_nome(texto: str) -> dict | None:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute("SELECT * FROM areas").fetchall()
    finally:
        conn.close()
    alvo = _normalizar(texto)
    for row in rows:
        area = dict(row)
        if alvo == _normalizar(area["id"]) or alvo == _normalizar(area["nome"]):
            return area
        if "salao" in alvo and "salao" in _normalizar(area["id"]):
            return area
        if "churrasc" in alvo and "churrasc" in _normalizar(area["id"]):
            return area
        if "quadra" in alvo and "quadra" in _normalizar(area["id"]):
            return area
    return None


def area_tem_taxa(area_id: str) -> bool:
    area = get_area(area_id) or find_area_by_nome(area_id)
    return bool(area and area["taxa"] > 0)


def resolver_area_id(area: str) -> str | None:
    found = get_area(area) or find_area_by_nome(area)
    return found["id"] if found else None


def listar_reservas(apartamento: str) -> list[dict]:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT codigo, area, data
            FROM reservas
            WHERE apartamento = ? AND ativa = 1
            ORDER BY data, codigo
            """,
            (apartamento,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def listar_visitantes(apartamento: str) -> list[dict]:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT nome, data
            FROM visitantes
            WHERE apartamento = ?
            ORDER BY data, nome
            """,
            (apartamento,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def data_disponivel(area_id: str, data: str) -> bool:
    init_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT 1 FROM reservas
            WHERE area = ? AND data = ? AND ativa = 1
            """,
            (area_id, data),
        ).fetchone()
        return row is None
    finally:
        conn.close()


def _codigos_existentes(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT codigo FROM reservas").fetchall()
    return {row["codigo"] for row in rows}


def _gerar_codigo(conn: sqlite3.Connection) -> str:
    existentes = _codigos_existentes(conn)
    while True:
        codigo = f"RSV-{random.randint(5000, 99999)}"
        if codigo not in existentes and codigo not in {
            "RSV-1377",
            "RSV-4821",
            "RSV-2950",
        }:
            return codigo


def criar_reserva(apartamento: str, area_id: str, data: str) -> dict:
    init_db()
    with _lock:
        conn = _connect()
        try:
            codigo = _gerar_codigo(conn)
            conn.execute(
                """
                INSERT INTO reservas (codigo, apartamento, area, data, ativa)
                VALUES (?, ?, ?, ?, 1)
                """,
                (codigo, apartamento, area_id, data),
            )
            conn.commit()
            return {"codigo": codigo, "area": area_id, "data": data}
        except sqlite3.IntegrityError as exc:
            conn.rollback()
            raise AreaOcupadaError(
                "Esta área já está reservada nesta data."
            ) from exc
        finally:
            conn.close()


def cancelar_reserva_do_apartamento(
    apartamento: str,
    *,
    area_id: str | None = None,
    data: str | None = None,
    codigo: str | None = None,
) -> dict | None:
    init_db()
    with _lock:
        conn = _connect()
        try:
            if codigo:
                row = conn.execute(
                    """
                    SELECT * FROM reservas
                    WHERE codigo = ? AND apartamento = ? AND ativa = 1
                    """,
                    (codigo, apartamento),
                ).fetchone()
            elif area_id and data:
                row = conn.execute(
                    """
                    SELECT * FROM reservas
                    WHERE area = ? AND data = ? AND apartamento = ? AND ativa = 1
                    """,
                    (area_id, data, apartamento),
                ).fetchone()
            else:
                return None
            if not row:
                return None
            conn.execute(
                "UPDATE reservas SET ativa = 0 WHERE codigo = ?",
                (row["codigo"],),
            )
            conn.commit()
            return {"codigo": row["codigo"], "area": row["area"], "data": row["data"]}
        finally:
            conn.close()


def autorizar_visitante(apartamento: str, nome: str, data: str) -> dict:
    init_db()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO visitantes (apartamento, nome, data)
                VALUES (?, ?, ?)
                """,
                (apartamento, nome, data),
            )
            conn.commit()
            return {"nome": nome, "data": data}
        finally:
            conn.close()


def salvar_sessao(session_id: str, user_id: str, apartamento: str) -> None:
    init_db()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessoes (session_id, user_id, apartamento)
                VALUES (?, ?, ?)
                """,
                (session_id, user_id, apartamento),
            )
            conn.commit()
        finally:
            conn.close()


def obter_sessao(session_id: str) -> dict | None:
    init_db()
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT * FROM sessoes WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_confirmacao(
    *,
    confirmation_id: str,
    session_id: str,
    function_call_id: str,
    invocation_id: str,
    acao: str,
    detalhes: dict,
) -> None:
    init_db()
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                INSERT INTO confirmacoes
                    (id, session_id, function_call_id, invocation_id, acao, detalhes, respondida)
                VALUES (?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(id) DO UPDATE SET
                    function_call_id = excluded.function_call_id,
                    invocation_id = excluded.invocation_id,
                    acao = excluded.acao,
                    detalhes = excluded.detalhes
                WHERE confirmacoes.respondida = 0
                """,
                (
                    confirmation_id,
                    session_id,
                    function_call_id,
                    invocation_id,
                    acao,
                    json.dumps(detalhes, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()


def listar_confirmacoes_pendentes(session_id: str) -> list[dict]:
    init_db()
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT id, acao, detalhes
            FROM confirmacoes
            WHERE session_id = ? AND respondida = 0
            """,
            (session_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "acao": row["acao"],
                "detalhes": json.loads(row["detalhes"]),
            }
            for row in rows
        ]
    finally:
        conn.close()


def obter_confirmacao(session_id: str, confirmation_id: str) -> dict | None:
    init_db()
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT * FROM confirmacoes
            WHERE session_id = ? AND id = ?
            """,
            (session_id, confirmation_id),
        ).fetchone()
        if not row:
            return None
        data = dict(row)
        data["detalhes"] = json.loads(data["detalhes"])
        return data
    finally:
        conn.close()


def marcar_confirmacao_respondida(session_id: str, confirmation_id: str) -> bool:
    init_db()
    with _lock:
        conn = _connect()
        try:
            cur = conn.execute(
                """
                UPDATE confirmacoes
                SET respondida = 1
                WHERE session_id = ? AND id = ? AND respondida = 0
                """,
                (session_id, confirmation_id),
            )
            conn.commit()
            return cur.rowcount == 1
        finally:
            conn.close()


def _normalizar(texto: str) -> str:
    mapa = str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc")
    return texto.lower().translate(mapa).replace("-", " ").strip()
