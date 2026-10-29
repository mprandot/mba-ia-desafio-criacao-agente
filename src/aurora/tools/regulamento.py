from __future__ import annotations

import re

from aurora.config import DADOS_DIR

_REGULAMENTO = DADOS_DIR / "regulamento.md"


def _capitulos() -> dict[str, str]:
    texto = _REGULAMENTO.read_text(encoding="utf-8")
    partes = re.split(r"(?=^## Capítulo)", texto, flags=re.MULTILINE)
    mapa: dict[str, str] = {}
    for parte in partes:
        match = re.match(r"^## (Capítulo [^\n]+)", parte)
        if match:
            mapa[match.group(1)] = parte.strip()
    return mapa


def _artigo(capitulo: str, numero: str) -> str | None:
    padrao = rf"(\*\*Art\. {re.escape(numero)}\.\*\*.*?)(?=\n\*\*Art\. |\n## |\Z)"
    match = re.search(padrao, capitulo, flags=re.DOTALL)
    return match.group(1).strip() if match else None


def consultar_regulamento(assunto: str) -> dict:
    """Consulta só o trecho do regulamento necessário para o assunto pedido."""
    chave = assunto.lower()
    capitulos = _capitulos()

    if "piscina" in chave:
        cap = next((c for t, c in capitulos.items() if "piscina" in t.lower()), "")
        if any(p in chave for p in ("hora", "funcion", "domingo", "abre", "fecha")):
            artigo = _artigo(cap, "22")
            if artigo:
                return {"trecho": artigo}
        return {"trecho": cap[:800] if cap else "Capítulo da piscina não encontrado."}

    mapeamento = (
        ("churrasc", "churrasqueira"),
        ("salão", "salão"),
        ("salao", "salão"),
        ("quadra", "quadra"),
        ("visit", "visitante"),
        ("reserva", "áreas comuns"),
        ("animal", "animais"),
        ("garagem", "garagem"),
        ("silêncio", "sossego"),
        ("silencio", "sossego"),
        ("assembleia", "assembleia"),
    )
    for termo, titulo_parte in mapeamento:
        if termo in chave:
            for titulo, corpo in capitulos.items():
                if titulo_parte in titulo.lower():
                    return {"trecho": corpo[:800]}
    return {
        "trecho": "Não encontrei um capítulo específico. Reformule o assunto com mais detalhe."
    }
