"""
Central configuration loader for the Summa backend.

Reads settings from settings.json located at the root of the backend package.
"""

import json
from pathlib import Path

# Resolve settings.json relative to this file (backend/config.py -> backend/settings.json)
_SETTINGS_PATH = Path(__file__).parent / "settings.json"

def _load_settings() -> dict:
    if not _SETTINGS_PATH.exists():
        raise FileNotFoundError(f"settings.json not found at {_SETTINGS_PATH}")
    with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

_settings = _load_settings()

# LLM
LLM_URL: str = _settings["llm"]["LLM_URL"]
LLM_MODEL: str = _settings["llm"]["LLM_MODEL"]
EMBED_MODEL: str = _settings["llm"]["EMBED_MODEL"]
LLM_TEMPERATURE: float = float(_settings["llm"]["LLM_TEMPERATURE"])

# API
API_URL: str = _settings["api"]["API_URL"]

# Locations
DATA_DIR: str = _settings["locations"]["DATA_DIR"]
CHROMA_DIR: str = _settings["locations"]["CHROMA_DIR"]

# Rerank
ENABLE_RERANK: bool = _settings["rerank"]["ENABLE_RERANK"].lower() == "true"
RERANK_MODEL: str = _settings["rerank"]["RERANK_MODEL"]
RERANK_FETCH_K: int = int(_settings["rerank"]["RERANK_FETCH_K"])
RERANK_TOP_N: int = int(_settings["rerank"]["RERANK_TOP_N"])

# RAG
CHUNK_SIZE: int = int(_settings["rag"]["CHUNK_SIZE"])
CHUNK_OVERLAP: int = int(_settings["rag"]["CHUNK_OVERLAP"])

# Whisper
WHISPER_MODEL: str = _settings["whisper"]["WHISPER_MODEL"]

# Logging
LOG_LEVEL: str = _settings["logging"]["LOG_LEVEL"]
LOG_FORMAT: str = _settings["logging"]["LOG_FORMAT"]
LOG_FILE: str | None = _settings["logging"]["LOG_FILE"]
