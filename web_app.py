"""
Web Application Server for LLM Wiki using Flask

Provides:
1. Main Chat / Query Interface (ChatGPT/Gemini/Claude style)
2. Document Upload & Ingestion Page (/sources)
3. Admin Dashboard (Status, Logs, Wiki Explorer, Lint, Reset)
"""

import os
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from config import SOURCES_DIR, WIKI_DIR, INDEX_FILE, LOG_FILE, init_environment
from wiki_manager import (
    ingest_new_sources,
    query_wiki,
    save_synthesis_to_wiki,
    lint_wiki,
    get_wiki_status,
    reset_wiki,
    get_all_wiki_pages,
)

init_environment()

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB max upload limit

ALLOWED_EXTENSIONS = {'.txt', '.md', '.docx', '.pdf', '.json', '.csv', '.html'}


def is_allowed_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


@app.route("/")
def page_chat():
    """Main Page: Chat / Query interface similar to Gemini / Claude."""
    return render_template("chat.html", active_page="chat")


@app.route("/upload")
def page_upload():
    """Upload & Ingestion page."""
    sources = [f.name for f in SOURCES_DIR.glob("*") if not f.name.startswith(".")]
    return render_template("upload.html", active_page="upload", sources=sources)


@app.route("/admin")
def page_admin():
    """Admin page: Status, logs, wiki pages explorer, lint, reset."""
    return render_template("admin.html", active_page="admin")


# API Routes

@app.route("/api/query", methods=["POST"])
def api_query():
    """Query the Wiki and synthesize an answer."""
    data = request.get_json() or {}
    query_text = data.get("query", "").strip()

    if not query_text:
        return jsonify({"error": "La question ne peut pas être vide."}), 400

    try:
        answer, relevant_files = query_wiki(query_text)
        return jsonify({
            "success": True,
            "answer": answer,
            "relevant_files": relevant_files
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/save-synthesis", methods=["POST"])
def api_save_synthesis():
    """Saves a synthesized query answer back into the Wiki as a persistent page."""
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()

    if not title or not content:
        return jsonify({"error": "Le titre et le contenu sont requis."}), 400

    try:
        filename = save_synthesis_to_wiki(title, content)
        return jsonify({
            "success": True,
            "filename": filename,
            "message": f"Fiche enregistrée dans le wiki : wiki/{filename}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Uploads document files to /sources."""
    if "files" not in request.files:
        return jsonify({"error": "Aucun fichier n'a été téléversé."}), 400

    files = request.files.getlist("files")
    saved_files = []
    errors = []

    for file in files:
        if file and file.filename:
            filename = secure_filename(file.filename)
            if not is_allowed_file(filename):
                errors.append(f"Format non supporté: {filename}")
                continue
            
            dest_path = SOURCES_DIR / filename
            file.save(dest_path)
            saved_files.append(filename)

    return jsonify({
        "success": True,
        "saved_files": saved_files,
        "errors": errors
    })


@app.route("/api/ingest", methods=["POST"])
def api_ingest():
    """Triggers incremental ingestion on /sources."""
    try:
        ingested = ingest_new_sources()
        return jsonify({
            "success": True,
            "ingested_files": ingested,
            "count": len(ingested)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/status", methods=["GET"])
def api_status():
    """Returns wiki status statistics."""
    try:
        stats = get_wiki_status()
        sources = [f.name for f in SOURCES_DIR.glob("*") if not f.name.startswith(".")]
        stats["sources_list"] = sources
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/logs", methods=["GET"])
def api_logs():
    """Returns log.md content."""
    if LOG_FILE.exists():
        return jsonify({"content": LOG_FILE.read_text(encoding="utf-8")})
    return jsonify({"content": "# Aucun log disponible"})


@app.route("/api/index", methods=["GET"])
def api_index():
    """Returns index.md content."""
    if INDEX_FILE.exists():
        return jsonify({"content": INDEX_FILE.read_text(encoding="utf-8")})
    return jsonify({"content": "# Aucun index disponible"})


@app.route("/api/wiki-pages", methods=["GET"])
def api_wiki_pages():
    """Returns list and contents of all wiki pages."""
    pages = get_all_wiki_pages()
    return jsonify({"pages": pages})


@app.route("/api/wiki-page/<path:filename>", methods=["GET"])
def api_wiki_page_detail(filename):
    """Returns detail of a specific wiki page."""
    page_path = WIKI_DIR / filename
    if page_path.exists() and page_path.is_file():
        return jsonify({"filename": filename, "content": page_path.read_text(encoding="utf-8")})
    
    from wiki_manager import get_target_wiki_path
    target = get_target_wiki_path(filename)
    if target.exists() and target.is_file():
        rel = target.relative_to(WIKI_DIR).as_posix()
        return jsonify({"filename": rel, "content": target.read_text(encoding="utf-8")})

    base = Path(filename).name
    for p in WIKI_DIR.rglob(base):
        if p.is_file():
            rel = p.relative_to(WIKI_DIR).as_posix()
            return jsonify({"filename": rel, "content": p.read_text(encoding="utf-8")})

    return jsonify({"error": "Page non trouvée."}), 404


@app.route("/api/lint", methods=["POST"])
def api_lint():
    """Runs Wiki Lint & Health Check."""
    try:
        report = lint_wiki()
        return jsonify({"success": True, "report": report})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """Resets the Wiki."""
    data = request.get_json() or {}
    hard = data.get("hard", False)
    try:
        reset_wiki(keep_sources=not hard)
        return jsonify({
            "success": True,
            "message": "Le Wiki a été réinitialisé avec succès !"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_local_ip():
    """Returns the primary local network IP address."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def run_server(host="0.0.0.0", port=5000, debug=False):
    """Runs the Flask web server bound to all interfaces (0.0.0.0)."""
    local_ip = get_local_ip()
    print("=" * 60)
    print(" 🌐 LLM Wiki Web Application running at:")
    print(f"    👉 Local:   http://localhost:{port}")
    print(f"    👉 Network: http://{local_ip}:{port}")
    print(f"    👉 Bound:   http://{host}:{port} (Toutes les interfaces réseau)")
    print("=" * 60)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
