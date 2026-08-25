# 🤖 AGENTS.md - Context & Project Handover Document for AI Agents

> **File Purpose:** This document provides a complete, accurate, and structured overview of the **LLM Wiki** codebase for any AI Agent or developer continuing work on this repository.

---

## 📌 Project Overview & Specification

This application is a Python implementation of **Andrej Karpathy's LLM Wiki** pattern ([Gist Specification](https://gist.githubusercontent.com/karpathy/442a6bf555914893e9891c11519de94f/raw/ac46de1ad27f92b28ac95459c782c07f6b8c964a/llm-wiki.md)).

Instead of traditional query-time RAG, the LLM incrementally compiles raw source documents into a persistent, interlinked Markdown wiki (`/wiki`) sitting between the user and raw sources (`/sources`).

### Mandatory Technical Constraints Implemented
1. **LiteLLM Integration**: API calls use the `litellm` library (`litellm.completion`).
2. **Strict Model Name**: The model parameter is strictly set to `"llm"` with `custom_llm_provider="openai"`.
3. **Environment Credentials**: Credentials are read from `LITELLM_PROXY_API_BASE` and `LITELLM_PROXY_API_KEY` (or `.env`).
4. **Karpathy Core Operations**:
   - `/sources` : Immutable raw input documents (`.txt`, `.md`, `.docx`, `.pdf`, `.json`, `.csv`).
   - `/wiki` : LLM-generated markdown pages (Entity pages, Concept pages, Source Summaries, Syntheses).
   - `wiki/index.md` : Auto-maintained catalog grouped by categories in French (*Entités*, *Concepts*, *Synthèses*, *Résumés de Sources*).
   - `wiki/log.md` : Append-only chronological record (`## [YYYY-MM-DD HH:MM] operation | description`).
   - **Incremental Updates** : File SHA256 hashing recorded in `wiki/.processed_sources.json` to skip un-modified sources.
5. **Language**: 100% French configuration for all system prompts, user prompts, generated pages, index sections, log entries, and web UI.
6. **Network Binding**: Web server bound to `0.0.0.0` (accessible via `localhost`, `127.0.0.1`, and LAN IP address).

---

## 📂 Codebase Architecture & File Map

```text
C:\Users\MaurayY\perso\llm-wiki\
├── app.py                # Main script entry point (launches Web App by default)
├── web_app.py            # Flask Web Application backend & REST API endpoints
├── llm_client.py         # LiteLLM completion client (model="llm", custom_llm_provider="openai", SSL patch)
├── wiki_manager.py       # Core business logic (Ingest, Index, Log, Query, Synthesis, Lint, Reset)
├── cli.py                # CLI argument parser & Interactive terminal shell
├── config.py             # Global configuration, env vars, paths & template initialization
├── requirements.txt      # Pinned Python dependencies list (litellm, openai, httpx, flask, pypdf, etc.)
├── .env                  # Local environment file (LITELLM_PROXY_API_BASE & LITELLM_PROXY_API_KEY)
├── .env.example          # Sample environment variables template
├── .gitignore            # Git exclusion rules (.env, venv/, sources/*, wiki/*, scratch/)
├── README.md             # Complete French user guide and setup documentation
├── AGENTS.md             # This AI Agent context handover document
├── static/
│   ├── style.css         # Modern Glassmorphism dark mode CSS design system
│   └── app.js            # Frontend JavaScript (Chat UI, File Upload, Markdown rendering, Modals)
├── templates/
│   ├── base.html         # Base HTML layout with Glassmorphism sidebar
│   ├── chat.html         # Main Page (ChatGPT / Gemini / Claude style query UI)
│   ├── upload.html       # Document Upload & Ingestion page
│   └── admin.html        # Admin Dashboard (Stats, Logs, Explorer, Lint, Reset)
├── sources/              # Input directory for raw source files (.pdf, .docx, .txt, .md, etc.)
└── wiki/                 # Generated persistent markdown pages + index.md + log.md
    ├── entities/         # Entity markdown pages (Entite_*.md)
    ├── concepts/         # Concept markdown pages (Concept_*.md)
    ├── sources/          # Source summary markdown pages (Source_*.md)
    ├── syntheses/        # Compounded synthesis markdown pages (Synthesis_*.md)
    ├── index.md          # Auto-maintained catalog by category
    ├── log.md            # Append-only chronological activity log
    └── .processed_sources.json
```

---

## 🔑 Key Code Details & Technical Criticalities

### 1. LiteLLM Client & SSL Proxy Patch (`llm_client.py`)
- Call method: `litellm.completion(model="llm", custom_llm_provider="openai", api_base=..., api_key=...)`.
- **CRITICAL PATCH**: Includes `ssl._create_default_https_context` and a monkey-patch on `requests.Session.send` (`verify=False`). Do **NOT** remove this patch; it is required to bypass SSL certificate verification errors in corporate proxy environments during tiktoken/HTTP calls.

### 2. Multi-Format Text Readers (`wiki_manager.py`)
- `.docx` files: Handled via `read_docx_file()` using pure-Python standard library `zipfile` and `xml.etree.ElementTree` (parses `word/document.xml`).
- `.pdf` files: Handled via `read_pdf_file()` using `pypdf.PdfReader`.
- Plain text / `.md`: Handled via safe UTF-8 / Latin-1 fallback reading.

### 3. Subcommands & Execution Modes
- `python app.py` or `python app.py web --port 5000`: Launches the Web App on `0.0.0.0:5000`.
- `python app.py ingest`: Command-line incremental ingestion.
- `python app.py query "Question"`: Command-line wiki query with filing option.
- `python app.py lint`: Command-line structural and semantic health check.
- `python app.py status`: Command-line statistics and log preview.
- `python app.py reset [--hard]`: Resets wiki pages, index, log, and manifest.
- `python app.py interactive`: Interactive terminal menu shell.

---

## 🛠️ Python Environment & Pinned Dependencies

- **Python Binary**: `.\venv\Scripts\python.exe` (Python 3.15 in venv)
- **Key Installed Packages** (`requirements.txt`):
  - `litellm==1.15.0`
  - `openai==1.30.0`
  - `httpx==0.27.2` (Pinned to `<0.28.0` to avoid breaking `proxies` parameter error in OpenAI client)
  - `flask==3.1.3`
  - `pypdf==6.16.1`
  - `python-dotenv==1.2.3`
  - `rich==15.0.0`
  - `legacy-cgi==2.6.4` (Required for Python 3.13+ standard library `cgi` module removal compatibility)

---

## 🎯 Current Project State

- [x] Karpathy LLM Wiki core logic implemented (`/sources`, `/wiki`, `index.md`, `log.md`, incremental manifest).
- [x] LiteLLM API proxy integration with model name `"llm"`.
- [x] Multi-format file support (`.txt`, `.md`, `.docx`, `.pdf`).
- [x] 100% French prompt and output configuration.
- [x] Reset mechanism (`reset` command and `--hard` mode).
- [x] Full Web Application (ChatGPT/Gemini/Claude UI, File Upload, Admin dashboard, Lint, Explorer, Reset).
- [x] Network binding set to `0.0.0.0` (accessible locally and on LAN).
- [x] `requirements.txt` generated and pinned.
- [x] Anonymous Git repository initialized on `main` branch with sensitive data excluded via `.gitignore`.

---

## 💡 Guidelines for Future AI Agents

1. **Preserve Model Name**: Always keep `MODEL_NAME = "llm"` and `custom_llm_provider="openai"` in LiteLLM completion calls.
2. **Preserve SSL Patch**: Do not delete the `requests.Session.send` monkey-patch in `llm_client.py`.
3. **Preserve French Prompts**: Keep system prompts instructed to output strictly in French.
4. **Preserve 0.0.0.0 Host Binding**: Ensure `run_server()` defaults to `host="0.0.0.0"`.
5. **Testing**: Run verification commands via `.\venv\Scripts\python.exe app.py status` or `.\venv\Scripts\python.exe app.py ingest` after editing python files.
