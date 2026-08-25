"""
Configuration Module for LLM Wiki

Manages environment variables, directory paths, and initialization.
Conforms strictly to Andrej Karpathy's LLM Wiki spec:
- Model name: "llm"
- Base URL from LITELLM_PROXY_API_BASE
- API key from LITELLM_PROXY_API_KEY
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Mandatory Environment Variables
LITELLM_PROXY_API_BASE = os.getenv("LITELLM_PROXY_API_BASE")
LITELLM_PROXY_API_KEY = os.getenv("LITELLM_PROXY_API_KEY")

# Mandatory Strict Model Name
MODEL_NAME = "llm"

# Language Configuration (default: French "fr")
WIKI_LANGUAGE = os.getenv("WIKI_LANGUAGE", "fr")

# Project Directories & Key Files
BASE_DIR = Path(__file__).parent.resolve()
SOURCES_DIR = BASE_DIR / "sources"
WIKI_DIR = BASE_DIR / "wiki"
WIKI_ENTITIES_DIR = WIKI_DIR / "entities"
WIKI_CONCEPTS_DIR = WIKI_DIR / "concepts"
WIKI_SOURCES_DIR = WIKI_DIR / "sources"
WIKI_SYNTHESES_DIR = WIKI_DIR / "syntheses"

INDEX_FILE = WIKI_DIR / "index.md"
LOG_FILE = WIKI_DIR / "log.md"
MANIFEST_FILE = WIKI_DIR / ".processed_sources.json"


def init_environment() -> None:
    """Ensure required directories (/sources, /wiki and subfolders) and initial files exist."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_ENTITIES_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_CONCEPTS_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    WIKI_SYNTHESES_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize index.md if it doesn't exist
    if not INDEX_FILE.exists():
        index_template = (
            "# Index du LLM Wiki\n\n"
            "Catalogue de toutes les pages du wiki, maintenu automatiquement par le LLM.\n\n"
            "## Entités\n\n"
            "## Concepts\n\n"
            "## Synthèses\n\n"
            "## Résumés de Sources\n\n"
        )
        INDEX_FILE.write_text(index_template, encoding="utf-8")

    # Initialize log.md if it doesn't exist
    if not LOG_FILE.exists():
        log_template = (
            "# Journal d'activité du LLM Wiki\n\n"
            "Registre chronologique cumulatif des ingestions, requêtes et audits (lint).\n\n"
        )
        LOG_FILE.write_text(log_template, encoding="utf-8")

