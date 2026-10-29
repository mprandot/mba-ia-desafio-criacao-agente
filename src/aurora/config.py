from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[2]
DADOS_DIR = ROOT_DIR / "dados"
RUNTIME_DIR = ROOT_DIR / ".aurora"
RUNTIME_DB = RUNTIME_DIR / "runtime.db"
SESSIONS_DB = RUNTIME_DIR / "sessions.db"

APP_NAME = "aurora"
MODEL = os.getenv("AURORA_MODEL", "gemini-2.5-flash")


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
